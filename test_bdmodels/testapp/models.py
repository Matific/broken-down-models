from django.conf import settings
from django.db import models

from bdmodels.models import BrokenDownModel
from bdmodels.fields import VirtualOneToOneField, VirtualParentLink


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
    parenta_ptr = VirtualOneToOneField(ParentA, 'id', parent_link=True, on_delete=models.DO_NOTHING)
    parentb_ptr = VirtualOneToOneField(ParentB, 'id', parent_link=True, on_delete=models.DO_NOTHING)
    parentc_ptr = VirtualOneToOneField(ParentC, 'id', parent_link=True, on_delete=models.DO_NOTHING)
    child_name = models.CharField(max_length=10)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)


class UserChild(BrokenDownModel, ParentA, ParentB, ParentC):
    id = models.AutoField(primary_key=True)
    parenta_ptr = VirtualOneToOneField(ParentA, 'id', parent_link=True, on_delete=models.DO_NOTHING)
    parentb_ptr = VirtualOneToOneField(ParentB, 'id', parent_link=True, on_delete=models.DO_NOTHING)
    parentc_ptr = VirtualOneToOneField(ParentC, 'id', parent_link=True, on_delete=models.DO_NOTHING)
    child_name = models.CharField(max_length=10)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # unlike above, not nullable


class ParentWithFK(models.Model):
    fkid = models.AutoField(primary_key=True)
    parfk_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)


class Nephew(BrokenDownModel, ParentA, ParentWithFK):
    id = models.AutoField(primary_key=True)
    parentwithfk_ptr = VirtualOneToOneField(ParentWithFK, 'id', parent_link=True, on_delete=models.DO_NOTHING)
    parenta_ptr = VirtualOneToOneField(ParentA, 'id', parent_link=True, on_delete=models.DO_NOTHING)


class TimeStampMixin(models.Model):
    """Adds timestamps to inheriting models."""

    class Meta:
        abstract = True

    created_on = models.DateTimeField(
        'created on',
        db_index=True,
        auto_now_add=True,
        editable=False, )

    last_modified = models.DateTimeField(
        'last modified',
        auto_now=True,
        editable=False, )


class TimeStampedChild(BrokenDownModel, TimeStampMixin, ParentA, ParentB, ParentC):
    id = models.AutoField(primary_key=True)
    parenta_ptr = VirtualOneToOneField(ParentA, 'id', parent_link=True, on_delete=models.DO_NOTHING)
    parentb_ptr = VirtualOneToOneField(ParentB, 'id', parent_link=True, on_delete=models.DO_NOTHING)
    parentc_ptr = VirtualOneToOneField(ParentC, 'id', parent_link=True, on_delete=models.DO_NOTHING)
    child_name = models.CharField(max_length=10)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)


class ChildProxy(Child):
    class Meta:
        proxy = True

    def dummy(self):
        """function available only on ChildProxy objects"""


class ChildWithVirtualNonParent(BrokenDownModel, ParentA):
    id = models.AutoField(primary_key=True)
    parenta_ptr = VirtualParentLink(ParentA, on_delete=models.DO_NOTHING)
    b = VirtualOneToOneField(ParentB, 'id', on_delete=models.DO_NOTHING)
    child_name = models.CharField(max_length=10)
