import warnings

from django.core import checks, exceptions
from django.db.models import (
    ForeignKey, OneToOneField,
    CASCADE, SET_NULL, SET_DEFAULT,
    NOT_PROVIDED, DEFERRED,
)
from django.db.models.fields.related import RECURSIVE_RELATIONSHIP_CONSTANT
from django.db.models.fields.related_descriptors import ForwardOneToOneDescriptor, ForwardManyToOneDescriptor
from django.utils.translation import gettext_lazy as _


class ReadOnlyForwardRelationDescriptor:
    # We do not really set anything here. Read-only. But Django mechanisms
    # will sometimes set it for us. When this is acceptable, we'll just ignore them.
    def __set__(self, instance, value):
        current_value = getattr(instance, self.field.attname, None)
        if value in (None, NOT_PROVIDED) and current_value in (None, NOT_PROVIDED):
            # ok, do nothing
            pass
        elif all(
                getattr(instance, lh_field.attname) == getattr(value, rh_field.attname)
                for lh_field, rh_field in self.field.related_fields
        ):
            # assignment to same value. No fuss
            pass
        else:
            raise ValueError('Cannot assign "%r": "%s.%s" is a virtual, read-only field' % (
                    value,
                    instance._meta.object_name,
                    self.field.name,
            ))


class VirtualForwardManyToOneDescriptor(ReadOnlyForwardRelationDescriptor, ForwardManyToOneDescriptor):
    pass


class VirtualForwardOneToOneDescriptor(ReadOnlyForwardRelationDescriptor, ForwardOneToOneDescriptor):
    pass


class VirtualForeignKey(ForeignKey):
    """
    A reference to a foreign object, based on an existing field

    This is just like a :py:class:`ForeignKey <django.db.models.ForeignKey>`
    with the exception that, rather than creating a related ``*_id`` field
    to hold the id of the referenced object, it uses one of the existing
    fields of the model.

    The name of the field to be used is given as the required parameter ``from_field``.

    Since the assumption is that the existing field serves other purposes
    (either it is interesting in itself, or the id it holds references
    more than one object), we limit changes through this field. Thus,
    Attempts to change the field's value are blocked. Accordingly,
    it must be non-editable, and its ``on_delete`` rule must not
    change the field's value. Similarly, a default does not make sense.

    Adding constraints would make sense -- but this is currently not supported.

    If an index is needed, it should be defined on the concrete field.
    """
    can_share_attribute = True
    forward_related_accessor_class = VirtualForwardManyToOneDescriptor

    description = _("Foreign object reference based on an existing field")

    def __init__(self, to, from_field, on_delete,
                 related_name=None, related_query_name=None,
                 limit_choices_to=None, parent_link=False, to_field=None,
                 db_constraint=False, **kwargs):
        try:
            to._meta.model_name
        except AttributeError:
            if not isinstance(to, str):
                raise ValueError(
                    "%s(%r) is invalid. First parameter to ForeignKey must be "
                    "either a model, a model name, or the string %r" % (
                        self.__class__.__name__, to,
                        RECURSIVE_RELATIONSHIP_CONSTANT,
                    )
                )
        else:
            # For backwards compatibility purposes, we need to *try* and set
            # the to_field during FK construction. It won't be guaranteed to
            # be correct until contribute_to_class is called. Refs #12190.
            to_field = to_field or (to._meta.pk and to._meta.pk.name)

        if 'default' in kwargs:
            raise ValueError("Virtual field cannot have a default")
        if 'editable' in kwargs:
            if kwargs['editable']:
                raise ValueError("Virtual field cannot be editable")
            else:
                warnings.warn("Virtual fields cannot be editable, editable=False is redundant")
        kwargs['editable'] = False
        if 'db_index' in kwargs:
            if kwargs['db_index']:
                raise ValueError(
                    f"Virtual field cannot create an index; add indexing on the concrete field "
                    f"({from_field}) instead"
                )
            else:
                warnings.warn("Virtual fields cannot have indexes, db_index=False is redundant")
        kwargs['db_index'] = False
        if db_constraint:
            warnings.warn("Constraints on virtual fields are not implemented yet")
            db_constraint = False

        kwargs['rel'] = self.rel_class(
            self, to, to_field,
            related_name=related_name,
            related_query_name=related_query_name,
            limit_choices_to=limit_choices_to,
            parent_link=parent_link,
            on_delete=on_delete,
        )
        super(ForeignKey, self).__init__(to, on_delete, from_fields=['self'], to_fields=[to_field], **kwargs)

        self.db_constraint = db_constraint
        self.from_field = from_field

    def set_attributes_from_name(self, name):
        super().set_attributes_from_name(name)
        self.concrete = False

    def check(self, **kwargs):
        return [
            *self._check_from_field(),
            *super().check(**kwargs),
            #  *self._check_on_delete(),  # included in super().check()
            #  *self._check_unique(),     # included in super().check()
        ]

    def _check_from_field(self):
        try:
            self.model._meta.get_field(self.from_field)
        except exceptions.FieldDoesNotExist:
            return [
                checks.Error(
                    "The VirtualForeignKey from_field references the "
                    "nonexistent field '%s'." % self.from_field,
                    obj=self,
                    id='bdmodels.E001',
                )
            ]
        else:
            return []

    def _check_on_delete(self):
        on_delete = getattr(self.remote_field, 'on_delete', None)
        if on_delete in (SET_NULL, SET_DEFAULT):
            return [
                checks.Error(
                    'A shared reference field specifies an on_delete rule which would make it change automatically.',
                    hint='Change the on_delete rule to preserve the value or delete the referencing object',
                    obj=self,
                    id='bdmodels.E002',
                )
            ]
        else:
            return []

    def deconstruct(self):
        """
        (This docstring had to be added to make Sphinx not include the parent's
        docstring for it in the class documentation. Parent docstring applies,
        as this changes implementation only)

        :meta private:
        """
        name, path, args, kwargs = super(ForeignKey, self).deconstruct()
        del kwargs['to_fields']
        del kwargs['from_fields']
        # Handle the simpler arguments
        kwargs['from_field'] = self.from_field
        kwargs.pop('db_index', None)
        del kwargs['editable']
        if self.db_constraint is not False:
            # For future use...
            kwargs['db_constraint'] = self.db_constraint
        # Rel needs more work.
        to_meta = getattr(self.remote_field.model, "_meta", None)
        if self.remote_field.field_name and (
                not to_meta or (to_meta.pk and self.remote_field.field_name != to_meta.pk.name)):
            kwargs['to_field'] = self.remote_field.field_name
        return name, path, args, kwargs

    def get_attname(self):
        return self.from_field

    def get_default(self):
        # Virtual fields do not have defaults. They must stay deferred.
        return DEFERRED

    def formfield(self, *, using=None, **kwargs):
        return super().formfield(using=using, disabled=True, **kwargs)


class VirtualOneToOneField(OneToOneField, VirtualForeignKey):
    """
    One-to-one relationship based on existing field

    This field is to a :py:class:`OneToOneField <django.db.models.OneToOneField>` as a
    :py:class:`VirtualForeignKey` is to a :py:class:`ForeignKey <django.db.models.ForeignKey>`,
    and vice versa -- it is also to :py:class:`VirtualForeignKey` as a
    :py:class:`OneToOneField <django.db.models.OneToOneField>` is to a
    :py:class:`ForeignKey <django.db.models.ForeignKey>`.
    """
    description = _("One-to-one relationship based on existing field")

    forward_related_accessor_class = VirtualForwardOneToOneDescriptor

    def __init__(self, to, from_field, on_delete, to_field=None, **kwargs):
        kwargs['unique'] = True
        super(OneToOneField, self).__init__(to, from_field, on_delete, to_field=to_field, **kwargs)


class VirtualParentLink(VirtualOneToOneField):
    """
    A :py:class:`VirtualOneToOneField` that is also a parent link

    The most common use for :py:class:`VirtualOneToOneField` while breaking down
    models is for a field that is also a link to a parent model, and whose base field
    is the model's primary key.

    This is mostly a shorthand for this use-case -- the ``parent_link`` attribute is
    set to ``True``, and the ``from_field`` has a default of ``'id'`` (using the model's
    actual PK is more involved, and is left for the future).
    """
    description = _("A VirtualOneToOneField that is also a parent link -- a common case")

    def __init__(self, to, from_field='id', on_delete=CASCADE, to_field=None, **kwargs):
        kwargs['parent_link'] = True
        super().__init__(to, from_field, on_delete, to_field=to_field, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if "parent_link" in kwargs:
            del kwargs['parent_link']
        return name, path, args, kwargs
