from django.conf import settings
from django.db import models

from bdmodels.models import BrokenDownModel, BrokenDownManager
from bdmodels.fields import VirtualOneToOneField2


class ParentA(models.Model):
    aid = models.AutoField(primary_key=True)
    para_name = models.CharField(max_length=10)
    para_zit = models.BooleanField(default=True)


class ParentB(models.Model):
    bid = models.AutoField(primary_key=True)
    parb_name = models.CharField(max_length=10)
    parb_zit = models.BooleanField(default=True)


class ParentC(models.Model):
    cid = models.AutoField(primary_key=True)
    parc_name = models.CharField(max_length=10)
    parc_zit = models.BooleanField(default=True)


class Child(BrokenDownModel, ParentA, ParentB, ParentC):
    id = models.AutoField(primary_key=True)
    child_name = models.CharField(max_length=10)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)


class UserChild(BrokenDownModel, ParentA, ParentB, ParentC):
    id = models.AutoField(primary_key=True)
    child_name = models.CharField(max_length=10)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # unlike above, not nullable


class PartialChild(BrokenDownModel, ParentA, ParentB, ParentC):
    id = models.AutoField(primary_key=True)
    child_name = models.CharField(max_length=10)
    parentb_ptr = models.OneToOneField(ParentB, parent_link=True, on_delete=models.DO_NOTHING)
    parentc_ptr = models.OneToOneField(ParentC, parent_link=True, null=True, on_delete=models.SET_NULL)


class ParentWithFK(models.Model):
    fkid = models.AutoField(primary_key=True)
    parfk_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)


class Nephew(BrokenDownModel, ParentA, ParentWithFK):
    pass


class VirtualChild(BrokenDownModel, ParentA, ParentB, ParentC):
    id = models.AutoField(primary_key=True)
    parenta_ptr = VirtualOneToOneField2(ParentA, 'id', parent_link=True, on_delete=models.DO_NOTHING)
    parentb_ptr = VirtualOneToOneField2(ParentB, 'id', parent_link=True, on_delete=models.DO_NOTHING)
    parentc_ptr = VirtualOneToOneField2(ParentC, 'id', parent_link=True, on_delete=models.DO_NOTHING)
    child_name = models.CharField(max_length=10)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

