from django.db import models
from django.db.models import PROTECT

from bdmodels.fields import VirtualParentLink
from bdmodels.models import BrokenDownModel


class Partial(models.Model):
    partial_id = models.IntegerField(primary_key=True)
    c = models.IntegerField(default=3)
    d = models.CharField(max_length=10, default="hi")


class BigModel(BrokenDownModel, Partial):
    id = models.AutoField(primary_key=True)
    partial_ptr = VirtualParentLink(Partial, on_delete=PROTECT)
    a = models.BooleanField(default=True)
    b = models.BooleanField(null=True)
