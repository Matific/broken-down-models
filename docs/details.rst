
.. _details:

What is really going on here
++++++++++++++++++++++++++++


General Idea
------------

Django already includes a mechanism where fields for one model are stored in
more than one table -- Multi Table Inheritance. That's what happens when we
do "normal" inheritance of models, without specifying anything special in
the Meta of either of the models.

If we have::

    from django.db import models

    class Parent(models.Model):
        parental = models.IntegerField()

    class Child(Parent):
        childish = models.BooleanField()

Then we can use the ``parental`` field on the ``Child`` class as if it was
defined there.  Multiple inheritance is also supported, and the following almost
works::

    from django.db import models

    class Mother(models.Model):
        motherly = models.IntegerField()

    class Father(models.Model):
        fatherly = models.IntegerField()

    # This DOES NOT WORK, just almost
    class Child(Mother, Father):
        locale = models.ForeignKey("localization.Locale")

So -- if we fix the little bump (details below), then we can break our large
model into many small pieces. We can throw any field that's currently on the
large model into its own model (and its own table); the large model will then
subclass all of them.  In principle, no other code will have to change.

Of course, that is a little too good to be true. Let us consider the...

Problems (and solutions)
------------------------
Field clash
===========

The first problem is that, as noted above, the models described above don't
actually work. both ``Mother`` and ``Father`` have a field named ``id`` (the
automatically generated PK), and the child cannot have two of them.

So, we just need to define explicitly the primary key fields on the parent
tables::

    from django.db import models

    class Mother(models.Model):
        mother_id = models.IntegerField(primary_key=True)
        motherly = models.IntegerField()

    class Father(models.Model):
        father_id = models.IntegerField(primary_key=True)
        fatherly = models.IntegerField()

    # Now this does work
    class Child(Mother, Father):
        locale = models.ForeignKey("localization.Locale")

Implicit Joins
==============

The above already allows us to reduce the size of the large table, which we
assume is the biggest problem. But still, with this, by default, queries on the
large model would join in all of the parts (as if we called ``select_related()``
with all of them); in most use-cases, this is redundant and wasteful.

The solution is to limit the fields, by default, to the ones on the actual child
model, by using the model _meta API to figure out which fields we want, and the
QuerySet ``only()`` method. A special manager class for broken-down models has a
``get_queryset()`` which sets this up.

Broken ``select_related()``
===========================

The solution to implicit joins works well. Actually, a little too well -- in
some cases, we'd want to have some part of the original model
``select_related()``-ed, but naively using ``only()`` in the manager blocks it:
Calling ``select_related()`` when all the relevant fields are deferred (by the
``only()`` call) achieves nothing. That is, as described so far,
::
    Child.objects.select_related('locale')

works as expected, but
::
    Child.objects.select_related('mother_ptr')

does not. Some special handling of ``select_related()`` is needed to make it
behave as expected; thus, we need the special manager to be based on a special
QuerySet class, and not just apply public API calls on a regular QuerySet.

Make accessed fields fetch their whole parent
=============================================

With the above scheme, fields coming from parents all become deferred. This
means that, when such a field is accessed for the first time, a database query
is made to fetch its value. We'd prefer that, if a query is already made, we'll
get all the fields from the relevant parent.

The way this query for the deferred field is done (internally in Django) is by
calling the model method :py:meth:`refresh_from_db()
<django.db.models.Model.refresh_from_db>`; that method can take an argument that
tells it exactly which fields to fetch. Usually, when getting the value of a
deferred field, the function is called with the name of that field only. We
override it and make sure that whenever it is given names, we complement the
list of names to include all the fields of relevant parent models.

Messed up id fields
===================

On one hand: With Mutli Table Inheritance, for each of the parents, the child gets
a ``parent_ptr`` one-to-one field -- which means, there's also a ``parent_ptr_id``
column in the table (and field in the model, which we care a lot less about).

On the other hand, the pointer-field to the first parent is also taken as the
Child's primary key -- by default, ``Child`` has no id field.

We can make our own primary-key id field, that's easy; but with the kind of use
we have in mind, we'd want all these ``..._ptr_id`` fields to also have just the
same value as the ``id`` field. In fact, we don't want them at all -- we'd much
prefer if the original ``id`` field is used instead. To achieve this, we need to
define these fields more-or-less explicitly, and set them to all point to the same
database column. This requires some messing with internals (Django isn't really
built to have columns shared between fields this way).

The solution involves a special type Foreign-Key field "family" -- ``VirtualForeignKey``,
``VirtualOneToOneField`` and ``VirtualParentLink``; the former does the heavy lifting,
and the latter two put a friendlier face on it. Making them work also requires some
changes in the Django model ``_meta`` implementation -- we define a subclass of the
relevant Django class (``django.db.model.options.Options``) and plug it into the model.
