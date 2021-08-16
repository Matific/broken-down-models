import itertools
import warnings

import django
from django.core import checks
from django.db import models, connections, transaction
from django.db.models.options import Options
from django.utils.functional import cached_property, partition


def get_field_names_to_fetch(model_set):
    fetched_fields = itertools.chain.from_iterable(
        model._meta.local_concrete_fields for model in model_set
    )
    fetched_field_names = [f.name for f in fetched_fields]
    return fetched_field_names


def _can_return_rows_from_bulk_insert(connection):
    return (
        connection.features.can_return_rows_from_bulk_insert
        if django.VERSION >= (3,) else
        connection.features.can_return_ids_from_bulk_insert
    )


class BrokenDownQuerySet(models.QuerySet):
    """
    Special queryset for use with broken-down models.
    """

    # Note for contributors: The main point of this class is to keep track of which parents
    # are set to be joined into the query and which aren't. We typically start with "none";
    # the manager's get_queryset() sets things up so that the deferrals are in sync with that,
    # and then we make sure they stay synced.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._with_parents = frozenset()

    def _clone(self):
        c = super()._clone()
        c._with_parents = self._with_parents
        return c

    @property
    def _concrete_model(self):
        return self.model._meta.concrete_model

    def select_related(self, *fields):
        """
        Fix :py:meth:`select_related() <django.db.models.query.QuerySet.select_related>` for correct
        handling of parent deferrals.

        .. note::
              Of necessity, this means that if a parent is select_related, previous "only"
              is overridden and ignored. We make no effort to distinguish between deferrals
              created manually by the user, and those created automatically to defer parents.
        """
        if fields:
            with_parents = set(self._with_parents)
            field_heads = set(field.split('__', 1)[0] for field in fields)
            for parent, link in self._concrete_model._meta.parents.items():
                if parent in with_parents:
                    continue

                ptr_name = link.name
                for field in field_heads:
                    if field == ptr_name:
                        with_parents.add(parent)
                        break
                    else:
                        field_obj = self.model._meta.get_field(field)
                        if field_obj.model == parent:
                            with_parents.add(parent)
                            break

            this = self.update_fetched_parents(with_parents)
            return super(BrokenDownQuerySet, this).select_related(*fields)
        else:
            return self.select_related_with_all_parents()

    def update_fetched_parents(self, parent_set, *, force_update_deferrals=False):
        """Update the set of fetched parents, and reset the set of deferred fields accordingly"""
        if (not force_update_deferrals) and parent_set == self._with_parents:
            return self

        fetched_field_names = self._get_field_names_to_fetch(parent_set)
        updated = self.only(*fetched_field_names)
        updated._with_parents = frozenset(parent_set)
        return updated
    update_fetched_parents.queryset_only = True

    def _get_field_names_to_fetch(self, parent_set):
        return get_field_names_to_fetch([self._concrete_model, *parent_set])

    def select_related_with_all_parents(self):
        updated = self.fetch_all_parents()
        updated = super(BrokenDownQuerySet, updated).select_related()
        return updated

    def fetch_all_parents(self):
        """
        Select all fields in the model for immediate fetching, as if this was not
        a broken-down model.

        This will make the query join all the parent tables.
        """
        updated = self.defer(None)
        updated._with_parents = frozenset(self.model._meta.parents.keys())
        return updated

    def bulk_create(self, objs, batch_size=None, ignore_conflicts=False):
        """
        Insert each of the instances into the database. Do *not* call
        save() on each of the instances, do not send any pre/post_save
        signals.

        Setting the primary key attribute, if it is not set, is required for broken-down
        models; so if the PK is an autoincrement field, the database feature
        ``can_return_rows_from_bulk_insert`` (``can_return_ids_from_bulk_insert`` on older
        Django versions) is required.
        """
        # Of importance: Broken-down models do the funny reverse thing where
        # the parents inherit their PK value from the child. So we only need
        # to do one id-returning insert, then fill in the PKs for the others
        # ourselves.
        if batch_size is not None and not batch_size > 0:
            raise ValueError("bulk_create batch size, if provided, must be positive")
        if not objs:
            return objs
        objs = list(objs)
        self._prepare_for_bulk_create(objs)
        # Drop proxies, use the concrete model
        model = self.model._meta.concrete_model
        meta = model._meta
        self._for_write = True
        connection = connections[self.db]
        objs_with_pk, objs_without_pk = partition(lambda o: o.pk is None, objs)
        if objs_without_pk and not _can_return_rows_from_bulk_insert(connection):
            raise ValueError(f"On {connection.vendor} bulk_create for broken-down models requires that PKs be set")
        with transaction.atomic(using=self.db, savepoint=False):
            # Start with the BDModel child
            fields = meta.local_concrete_fields
            if objs_with_pk:
                returned_columns = self._batched_insert(objs_with_pk, fields, batch_size, ignore_conflicts=ignore_conflicts)
                self._set_fields_from_returned_columns(objs_with_pk, returned_columns, meta, set_pk=False)
            if objs_without_pk:
                fields = [f for f in fields if not isinstance(f, models.AutoField)]
                returned_columns = self._batched_insert(objs_without_pk, fields, batch_size, ignore_conflicts=ignore_conflicts)
                if _can_return_rows_from_bulk_insert(connection) and not ignore_conflicts:
                    assert len(returned_columns) == len(objs_without_pk)
                self._set_fields_from_returned_columns(objs_without_pk, returned_columns, meta, set_pk=True)
            # Now everyone has PKs, we can proceed with objs
            for parent, field in meta.parents.items():
                # Make sure the link fields are synced with parent.
                if field:
                    self._sync_parent_pks_to_pk(objs, parent)
                    parent._base_manager.get_queryset()._batched_insert(
                        objs, parent._meta.local_concrete_fields, batch_size, ignore_conflicts=ignore_conflicts
                    )
            for obj in objs:
                obj._state.adding = False
                obj._state.db = self.db
        return objs

    def delete(self):
        # Prevent extra queries when looking up parents for deletion
        this = self.fetch_all_parents()
        return super(BrokenDownQuerySet, this).delete()

    @staticmethod
    def _set_fields_from_returned_columns(objs, returned_columns, opts, *, set_pk):
        """This implementation works with Django>=3.0"""
        for obj, results in zip(objs, returned_columns):
            for result, field in zip(results, opts.db_returning_fields):
                if set_pk or field != opts.pk:
                    setattr(obj, field.attname, result)

    @staticmethod
    def _sync_parent_pks_to_pk(objs, parent):
        parent_pk_attname = parent._meta.pk.attname
        for obj in objs:
            parent_pk = getattr(obj, parent_pk_attname)
            if parent_pk is None:
                setattr(obj, parent_pk_attname, obj.pk)
            elif parent_pk != obj.pk:
                raise ValueError(f"Broken-Down object {obj} has part {parent} with inconsistent id {parent_pk}")

    if django.VERSION < (3,):
        @staticmethod  # noqa: F811  # Python<3.9 says this is the line of the method def
        def _set_fields_from_returned_columns(objs, returned_columns, _, *, set_pk):  # noqa: F811  # Redefined on purpose
            """This implementation works with Django<3.0"""
            if not set_pk:
                return
            for obj, pk in zip(objs, returned_columns):
                obj.pk = pk

    if django.VERSION < (3, 2,):
        def _prepare_for_bulk_create(self, objs):
            return self._populate_pk_values(objs)


class BrokenDownManager(models.Manager.from_queryset(BrokenDownQuerySet)):
    """
    Basic Manager for broken-down models.

    Connects the model to a :py:class:`BrokenDownQuerySet` (and inherits its methods, as it is built from it).
    """
    def get_queryset(self):
        return super().get_queryset().update_fetched_parents({}, force_update_deferrals=True)


class BrokenDownOptions(Options):
    @cached_property
    def _forward_fields_map(self):
        res = {}
        fields = self._get_fields(reverse=False)
        for field in fields:
            res[field.name] = field
            # Due to the way Django's internals work, get_field() should also
            # be able to fetch a field by attname. In the case of a concrete
            # field with relation, includes the *_id name too

            # except for fields which share attributes, we don't want them in this game
            if getattr(field, 'can_share_attribute', False):
                continue
            try:
                res[field.attname] = field
            except AttributeError:
                pass
        return res


class BrokenDownModelBase(models.base.ModelBase):
    """A hack for using our own options class"""
    def add_to_class(cls, name, value):
        if name == '_meta':
            # We only mess with 'vanilla' Options
            if type(value) == Options:
                value.__class__ = BrokenDownOptions
            else:
                # If anybody else already messed with it, we bail out
                raise TypeError(f"BrokenDownModel needs to mess with the Options, but we got {type(value)}")
        super().add_to_class(name, value)


class BrokenDownModel(models.Model, metaclass=BrokenDownModelBase):
    """
    Base class to replace :py:class:`models.Model <django.db.models.Model>` for
    broken-down models.

    When using it, make sure to make it the first base-class of your model, so
    that its modified metaclass replaces the regular Model metaclass.

    It also specifies its own Manager, :py:class:`BrokenDownManager`; if you have
    custom managers on your model, use that as your base manager.

    Some :py:class:`Model <django.db.models.Model>` methods are overridden just
    to change their implementation; notably, some checks are reimplemented and
    some checks are added.

    The methods documented here are those which add functionality.
    """
    class Meta:
        abstract = True

    objects = BrokenDownManager()

    def getattr_if_loaded(self, attr: str, default=None):
        """
        Access an attribute (field), only if set specifically for the instance.
        This allows querying fields without causing unnecessary database round-trips.
        """
        if attr not in self.__dict__ and not hasattr(type(self), attr):
            warnings.warn(f"{self._meta.label} instance has no attribute '{attr}'")
        return self.__dict__.get(attr, default)

    def delete(self, using=None, keep_parents=False):
        opts = self._concrete_meta
        parents = opts.parents.keys()
        all_fields = get_field_names_to_fetch(parents)
        self.refresh_from_db(using=using, fields=all_fields)  # TODO: Use .refresh_from_db(all_parents=True)
        return super().delete(using=using, keep_parents=keep_parents)

    def refresh_from_db(self, using=None, fields=None, *, all_parents: bool = False):
        """
        This method is overridden for two purposes.

        One is to make sure fetching any parent attribute fetches the whole parent.

        The other is to add the ``all_parents`` argument, which can be used to reload
        the object in full, canceling deferrals. Since ``all_parents`` makes the model
        load all the fields, using it together with ``fields`` makes no sense and is
        an error.
        """
        opts = self._concrete_meta
        if fields:
            if all_parents:
                raise ValueError("refresh_from_db() with all_parents=True and specific fields makes no sense")
            parents = set(opts.get_field(name).model for name in fields)
            all_fields = get_field_names_to_fetch(parents)
            # Take special care *not* to override fields which have been set on the object,
            # unless they were specifically requested for refresh
            fields = list(set(all_fields) - set(self.__dict__.keys()) | set(fields))
        elif all_parents:
            fields = [field.name for field in opts.concrete_fields]
        super().refresh_from_db(using, fields)

    @property
    def _concrete_meta(self):
        return self._meta.concrete_model._meta

    @classmethod
    def check(cls, **kwargs):
        return [
            *super().check(**kwargs),
            *cls._check_nonvirtual_parents(),
        ]

    @classmethod
    def _check_field_name_clashes(cls):
        """Forbid field shadowing in multi-table inheritance."""
        errors = []
        used_fields = {}  # name or attname -> field

        # Check that multi-inheritance doesn't cause field name shadowing.
        for parent in cls._meta.get_parent_list():
            for f in parent._meta.local_fields:
                # This is the change from standard Model.
                # Original says: clash = used_fields.get(f.name) or used_fields.get(f.attname) or None
                clash = used_fields.get(f.name) or None
                if (not clash) and not getattr(f, 'can_share_attribute', False):
                    clash = used_fields.get(f.attname) or None
                if clash:
                    errors.append(
                        checks.Error(
                            "The field '%s' from parent model "
                            "'%s' clashes with the field '%s' "
                            "from parent model '%s'." % (
                                clash.name, clash.model._meta,
                                f.name, f.model._meta
                            ),
                            obj=cls,
                            id='models.E005',
                        )
                    )
                used_fields[f.name] = f
                used_fields[f.attname] = f

        # Check that fields defined in the model don't clash with fields from
        # parents, including auto-generated fields like multi-table inheritance
        # child accessors.

        for parent in cls._meta.get_parent_list():
            for f in parent._meta.get_fields():
                if f not in used_fields:
                    used_fields[f.name] = f

        for f in cls._meta.local_fields:
            # This is the change from standard Model.
            # Original says: clash = used_fields.get(f.name) or used_fields.get(f.attname) or None
            clash = used_fields.get(f.name) or None
            if (not clash) and not getattr(f, 'can_share_attribute', False):
                clash = used_fields.get(f.attname) or None
            # Note that we may detect clash between user-defined non-unique
            # field "id" and automatically added unique field "id", both
            # defined at the same model. This special case is considered in
            # _check_id_field and here we ignore it.
            id_conflict = f.name == "id" and clash and clash.name == "id" and clash.model == cls
            if clash and not id_conflict:
                errors.append(
                    checks.Error(
                        "The field '%s' clashes with the field '%s' "
                        "from model '%s'." % (
                            f.name, clash.name, clash.model._meta
                        ),
                        obj=f,
                        id='models.E006',
                    )
                )
            used_fields[f.name] = f
            used_fields[f.attname] = f

        return errors

    @classmethod
    def _check_column_name_clashes(cls):
        # Store a list of column names which have already been used by other fields.
        used_column_names = []
        errors = []

        for f in cls._meta.local_fields:
            # This is the change from standard Model.
            # We don't want attribute-sharing fields to play here
            if getattr(f, 'can_share_attribute', False):
                continue
            # From here on, as parent
            _, column_name = f.get_attname_column()

            # Ensure the column name is not already in use.
            if column_name and column_name in used_column_names:
                errors.append(
                    checks.Error(
                        "Field '%s' has column name '%s' that is used by "
                        "another field." % (f.name, column_name),
                        hint="Specify a 'db_column' for the field.",
                        obj=cls,
                        id='models.E007'
                    )
                )
            else:
                used_column_names.append(column_name)

        return errors

    @classmethod
    def _check_nonvirtual_parents(cls):
        """Non-virtual MTI parents do not work for broken-down models"""
        errors = [
            checks.Error(
                f"Field '{f.name}' is a link to a parent model (using MTI) but is not a virtual field. "
                f"This is not supported in Broken-Down Models.",
                hint="Define a VirtualOneToOneField or VirtualParentLink for the parent link",
                obj=cls,
                id='bdmodels.E003'
            )
            for f in cls._meta.local_fields
            if (
                    isinstance(f, models.OneToOneField) and
                    (f.auto_created or getattr(f, 'parent_link', False)) and
                    not getattr(f, 'can_share_attribute', False)
            )
        ]
        return errors

    def save_base(self, *, force_insert=False, **kwargs):
        if force_insert or self.pk is None:
            # We need to reverse the order that saving is usually done for the case of inserting.
            # First save ourselves (and get an id), only then save parents
            self._reversed_save_base(force_insert=force_insert, **kwargs)
        else:
            super().save_base(force_insert=force_insert, **kwargs)

    save_base.alters_data = True

    def _reversed_save_base(self, raw=False, force_insert=False,
                            force_update=False, using=None, update_fields=None):
        """
        The 'raw' argument is telling save_base not to save any parent
        models and not to do any changes to the values before save. This
        is used by fixture loading.
        """
        from django.db.models.signals import pre_save, post_save

        from django.db import router, transaction

        using = using or router.db_for_write(self.__class__, instance=self)
        assert not (force_insert and (force_update or update_fields))
        assert update_fields is None or update_fields
        cls = origin = self.__class__
        # Skip proxies, but keep the origin as the proxy model.
        if cls._meta.proxy:
            cls = cls._meta.concrete_model
        meta = cls._meta
        if not meta.auto_created:
            pre_save.send(
                sender=origin, instance=self, raw=raw, using=using,
                update_fields=update_fields,
            )
        # A transaction isn't needed if one query is issued.
        if meta.parents:
            context_manager = transaction.atomic(using=using, savepoint=False)
        else:
            context_manager = transaction.mark_for_rollback_on_error(using=using)
        with context_manager:
            # In this block we change the order of calls
            updated = self._save_table(
                raw, cls, force_insert,
                force_update, using, update_fields,
            )
            if not raw:
                self._save_parents(cls, using, update_fields)
        # Store the database on which the object was saved
        self._state.db = using
        # Once saved, this is no longer a to-be-added instance.
        self._state.adding = False

        # Signal that the save is complete
        if not meta.auto_created:
            post_save.send(
                sender=origin, instance=self, created=(not updated),
                update_fields=update_fields, raw=raw, using=using,
            )
