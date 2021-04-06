from django.db import models

from bdmodels.models import BrokenDownModel, BrokenDownManager


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

    objects = BrokenDownManager()


class PartialChild(BrokenDownModel, ParentA, ParentB, ParentC):
    id = models.AutoField(primary_key=True)
    child_name = models.CharField(max_length=10)
    parentb_ptr = models.OneToOneField(ParentB, parent_link=True, on_delete=models.DO_NOTHING)
    parentc_ptr = models.OneToOneField(ParentC, parent_link=True, null=True, on_delete=models.SET_NULL)
