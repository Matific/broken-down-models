"""
Model inheritance

Copied from Django's tests. Kept only the multi-table inheritance
part, and modified it to use broken-down models

TODO: This doesn't work for now, because VirtualOneToOneField doesn't really work without migrations.
TODO: (it needs to be connected to the database column, but when created, it needs to be at the model
TODO: level only, not at the database level; and without migrations, there's no SeparateDatabaseAndState)
"""
from django.db import models

from bdmodels.fields import VirtualOneToOneField
from bdmodels.models import BrokenDownModel

#
# Multi-table inheritance
#


class Chef(models.Model):
    name = models.CharField(max_length=50)


class Place(models.Model):
    place_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    address = models.CharField(max_length=80)


class Rating(models.Model):
    rating = models.IntegerField(null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ['-rating']


class Restaurant(BrokenDownModel, Place, Rating):
    id = models.AutoField(primary_key=True)
    place_ptr = VirtualOneToOneField(Place, 'id', parent_link=True, on_delete=models.CASCADE)
    serves_hot_dogs = models.BooleanField(default=False)
    serves_pizza = models.BooleanField(default=False)
    chef = models.ForeignKey(Chef, models.SET_NULL, null=True, blank=True)

    class Meta(Rating.Meta):
        db_table = 'my_restaurant'


class ItalianRestaurant(Restaurant):
    serves_gnocchi = models.BooleanField(default=False)


class Supplier(Place):
    id = models.AutoField(primary_key=True)
    place_ptr = VirtualOneToOneField(Place, 'id', parent_link=True, on_delete=models.CASCADE)
    customers = models.ManyToManyField(Restaurant, related_name='provider')


class ParkingLot(Place):
    # An explicit link to the parent (we can control the attribute name).
    parent = models.OneToOneField(Place, models.CASCADE, primary_key=True, parent_link=True)
    main_site = models.ForeignKey(Place, models.CASCADE, related_name='lot')


#
# Abstract base classes with related models where the sub-class has the
# same name in a different app and inherits from the same abstract base
# class.
# NOTE: The actual API tests for the following classes are in
#       model_inheritance_same_model_name/models.py - They are defined
#       here in order to have the name conflict between apps
#

class Title(models.Model):
    title = models.CharField(max_length=50)


class NamedURL(models.Model):
    title = models.ForeignKey(Title, models.CASCADE, related_name='attached_%(app_label)s_%(class)s_set')
    url = models.URLField()

    class Meta:
        abstract = True


class Mixin:
    def __init__(self):
        self.other_attr = 1
        super().__init__()


class MixinModel(models.Model, Mixin):
    pass


class Base(models.Model):
    titles = models.ManyToManyField(Title)


class SubBase(BrokenDownModel, Base):
    sub_id = models.IntegerField(primary_key=True)
    base_ptr = VirtualOneToOneField(Base, 'sub_id', parent_link=True, on_delete=models.CASCADE)


class GrandParent(models.Model):
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    email = models.EmailField(unique=True)
    place = models.ForeignKey(Place, models.CASCADE, null=True, related_name='+')

    class Meta:
        # Ordering used by test_inherited_ordering_pk_desc.
        ordering = ['-pk']
        unique_together = ('first_name', 'last_name')


class Parent(GrandParent):
    pass


class Child(Parent):
    pass


class GrandChild(Child):
    pass
