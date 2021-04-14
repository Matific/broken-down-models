from django import forms
from django.core import checks, exceptions
from django.db import router
from django.db.models import (
    ForeignKey, ForeignObject, ManyToOneRel, OneToOneField, OneToOneRel,
    SET_NULL, SET_DEFAULT,
    NOT_PROVIDED,
)
from django.db.models.fields.related import RECURSIVE_RELATIONSHIP_CONSTANT
from django.db.models.fields.related_descriptors import ReverseOneToOneDescriptor, ForwardOneToOneDescriptor, \
    ForwardManyToOneDescriptor
from django.db.models.query_utils import PathInfo
from django.utils.translation import gettext_lazy as _


class VirtualForeignKey(ForeignObject):
    """
    Provide a many-to-one relation without adding a column to the local model.
    This is just like a ForeignKey, except that it reuses an existing field
    to hold the remote value -- thereby allowing that field to be shared
    by several foreign references.
    """
    # Field flags
    many_to_many = False
    many_to_one = True
    one_to_many = False
    one_to_one = False
    editable = False

    rel_class = ManyToOneRel

    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _('%(model)s instance with %(field)s %(value)r does not exist.')
    }
    description = _("Foreign object reference based on an existing field")

    def __init__(self, to, from_field, on_delete,
                 related_name=None, related_query_name=None,
                 limit_choices_to=None, parent_link=False, to_field=None,
                 db_constraint=True, **kwargs):
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

        kwargs['rel'] = self.rel_class(
            self, to, to_field,
            related_name=related_name,
            related_query_name=related_query_name,
            limit_choices_to=limit_choices_to,
            parent_link=parent_link,
            on_delete=on_delete,
        )
        super().__init__(to, on_delete, from_fields=['self'], to_fields=[to_field], editable=False, **kwargs)

        self.db_constraint = db_constraint
        self.from_field = from_field

    def check(self, **kwargs):
        return [
            *super().check(**kwargs),
            *self._check_from_field(),
            *self._check_on_delete(),
            *self._check_unique(),
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

    # EXACT_COPY ForeignKey
    def _check_unique(self):
        return [
            checks.Warning(
                'Setting unique=True on a ForeignKey has the same effect as using a OneToOneField.',
                hint='ForeignKey(unique=True) is usually better served by a OneToOneField.',
                obj=self,
                id='fields.W342',
            )
        ] if self.unique else []

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs['to_fields']
        del kwargs['from_fields']
        # Handle the simpler arguments
        kwargs['from_field'] = self.from_field
        if self.db_index:
            del kwargs['db_index']
        else:
            kwargs['db_index'] = False
        if self.db_constraint is not True:
            kwargs['db_constraint'] = self.db_constraint
        # Rel needs more work.
        to_meta = getattr(self.remote_field.model, "_meta", None)
        if self.remote_field.field_name and (
                not to_meta or (to_meta.pk and self.remote_field.field_name != to_meta.pk.name)):
            kwargs['to_field'] = self.remote_field.field_name
        return name, path, args, kwargs

    # EXACT_COPY ForeignKey
    def to_python(self, value):
        return self.target_field.to_python(value)

    # EXACT_COPY ForeignKey
    @property
    def target_field(self):
        return self.foreign_related_fields[0]

    # EXACT_COPY ForeignKey
    def get_reverse_path_info(self, filtered_relation=None):
        """Get path from the related model to this field's model."""
        opts = self.model._meta
        from_opts = self.remote_field.model._meta
        return [PathInfo(
            from_opts=from_opts,
            to_opts=opts,
            target_fields=(opts.pk,),
            join_field=self.remote_field,
            m2m=not self.unique,
            direct=False,
            filtered_relation=filtered_relation,
        )]

    # EXACT_COPY ForeignKey
    def validate(self, value, model_instance):
        if self.remote_field.parent_link:
            return
        super().validate(value, model_instance)
        if value is None:
            return

        using = router.db_for_read(self.remote_field.model, instance=model_instance)
        qs = self.remote_field.model._default_manager.using(using).filter(
            **{self.remote_field.field_name: value}
        )
        qs = qs.complex_filter(self.get_limit_choices_to())
        if not qs.exists():
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={
                    'model': self.remote_field.model._meta.verbose_name, 'pk': value,
                    'field': self.remote_field.field_name, 'value': value,
                },  # 'pk' is included for backwards compatibility
            )

    def get_attname(self):
        return self.from_field

    # def get_attname_column(self):
    #     attname = self.get_attname()
    #     src_field = self.model._meta.get_field(attname)
    #     column = src_field.db_column or attname
    #     return attname, column

    def get_default(self):
        """Virtual fields do not have defaults"""
        return NOT_PROVIDED

    # EXACT_COPY ForeignKey
    def get_db_prep_save(self, value, connection):
        if value is None or (value == '' and
                             (not self.target_field.empty_strings_allowed or
                              connection.features.interprets_empty_strings_as_nulls)):
            return None
        else:
            return self.target_field.get_db_prep_save(value, connection=connection)

    # EXACT_COPY ForeignKey
    def get_db_prep_value(self, value, connection, prepared=False):
        return self.target_field.get_db_prep_value(value, connection, prepared)

    # EXACT_COPY ForeignKey
    def contribute_to_related_class(self, cls, related):
        super().contribute_to_related_class(cls, related)
        if self.remote_field.field_name is None:
            self.remote_field.field_name = cls._meta.pk.name

    # EQUIVALENT ForeignKey: return super().formfield(using=using, disabled=True, **kwargs)
    def formfield(self, *, using=None, **kwargs):
        if isinstance(self.remote_field.model, str):
            raise ValueError("Cannot create form field for %r yet, because "
                             "its related model %r has not been loaded yet" %
                             (self.name, self.remote_field.model))
        return super().formfield(**{
            'form_class': forms.ModelChoiceField,
            'queryset': self.remote_field.model._default_manager.using(using),
            'to_field_name': self.remote_field.field_name,
            'disabled': True,  # Not really editable
            **kwargs,
        })

    # EXACT_COPY ForeignKey
    def db_check(self, connection):
        return []

    # EXACT_COPY ForeignKey
    def db_type(self, connection):
        return self.target_field.rel_db_type(connection=connection)

    # EXACT_COPY ForeignKey
    def db_parameters(self, connection):
        return {"type": self.db_type(connection), "check": self.db_check(connection)}

    # EXACT_COPY ForeignKey
    def get_col(self, alias, output_field=None):
        if output_field is None:
            output_field = self.target_field
            while isinstance(output_field, (ForeignKey, VirtualForeignKey)):
                output_field = output_field.target_field
                if output_field is self:
                    raise ValueError('Cannot resolve output_field.')
        return super().get_col(alias, output_field)


class VirtualOneToOneField(OneToOneField, VirtualForeignKey):
    """
    A VirtualOneToOneField is essentially the same as a VirtualForeignKey,
    with the exception that it always carries a "unique" constraint with it
    and the reverse relation always returns the object pointed to (since there
    will only ever be one), rather than returning a list.
    """

    # Field flags
    many_to_many = False
    many_to_one = False
    one_to_many = False
    one_to_one = True

    related_accessor_class = ReverseOneToOneDescriptor
    forward_related_accessor_class = ForwardOneToOneDescriptor
    rel_class = OneToOneRel

    description = _("One-to-one relationship based on existing field")

    def __init__(self, to, from_field, on_delete, to_field=None, **kwargs):
        kwargs['unique'] = True
        super(OneToOneField, self).__init__(to, from_field, on_delete, to_field=to_field, **kwargs)

    # EXACT_COPY OneToOneField
    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if "unique" in kwargs:
            del kwargs['unique']
        return name, path, args, kwargs

    # EXACT_COPY OneToOneField
    def formfield(self, **kwargs):
        if self.remote_field.parent_link:
            return None
        return super().formfield(**kwargs)

    # EXACT_COPY OneToOneField
    def save_form_data(self, instance, data):
        if isinstance(data, self.remote_field.model):
            setattr(instance, self.name, data)
        else:
            setattr(instance, self.attname, data)

    # EXACT_COPY OneToOneField
    def _check_unique(self, **kwargs):
        # Override ForeignKey since check isn't applicable here.
        return []


# print(VirtualOneToOneField.__mro__)

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


class VirtualForeignKey2(ForeignKey):

    can_share_attribute = True
    forward_related_accessor_class = VirtualForwardManyToOneDescriptor

    description = _("Foreign object reference based on an existing field")

    def __init__(self, to, from_field, on_delete,
                 related_name=None, related_query_name=None,
                 limit_choices_to=None, parent_link=False, to_field=None,
                 db_constraint=True, **kwargs):
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

        kwargs['rel'] = self.rel_class(
            self, to, to_field,
            related_name=related_name,
            related_query_name=related_query_name,
            limit_choices_to=limit_choices_to,
            parent_link=parent_link,
            on_delete=on_delete,
        )
        kwargs['editable'] = False
        super(ForeignKey, self).__init__(to, on_delete, from_fields=['self'], to_fields=[to_field], **kwargs)

        self.db_constraint = db_constraint
        self.from_field = from_field

    def set_attributes_from_name(self, name):
        super().set_attributes_from_name(name)
        self.concrete = False

    def check(self, **kwargs):
        return [
            *super().check(**kwargs),
            *self._check_from_field(),
            *self._check_on_delete(),
            *self._check_unique(),
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

    # Suspected equivalent: n,p,a,kw=super().deconstruct(); kw['from_field']=self.from_field
    def deconstruct(self):
        name, path, args, kwargs = super(ForeignKey, self).deconstruct()
        del kwargs['to_fields']
        del kwargs['from_fields']
        # Handle the simpler arguments
        kwargs['from_field'] = self.from_field
        if self.db_index:
            del kwargs['db_index']
        else:
            kwargs['db_index'] = False
        if self.db_constraint is not True:
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
        """Virtual fields do not have defaults, and must rely on the from_field"""
        return self.model._meta.get_field(self.from_field).get_default()

    def formfield(self, *, using=None, **kwargs):
        return super().formfield(using=using, disabled=True, **kwargs)


class VirtualOneToOneField2(OneToOneField, VirtualForeignKey2):
    description = _("One-to-one relationship based on existing field")

    forward_related_accessor_class = VirtualForwardOneToOneDescriptor

    def __init__(self, to, from_field, on_delete, to_field=None, **kwargs):
        kwargs['unique'] = True
        super(OneToOneField, self).__init__(to, from_field, on_delete, to_field=to_field, **kwargs)
