Break a large model down, transparently
---------------------------------------

In a project that goes on for several years, models tend to grow and
accumulate fields. If you aren't very disciplined about this, you wake up
one day, and find that one of your central tables, one with millions of
rows, has 43 columns, including some TextFields. Most of them are not
required most of the time, but the default (and common) use is to fetch all
of them; also, since this table is queried a lot, the mere fact that it has
so many columns makes some of the access slower.

When you realize that, you want to break it into components, such that
only a few, most-important columns will participate in the large searches,
while further details will be searched and fetched only when needed.

But that is a scary proposition -- it might involve subtle code changes,
break not just field access but also ORM queries... and this is a central
model. The change imagined is open-heart surgery on a large project.
Maybe, if we look the other way, it won't bother us too much...

**broken-down-models** is here to help you. This is a library which can
help you refactor your large model into a set of smaller ones, each with
its own database table, while most of your project code remains unchanged.

How?
----

Django already includes a mechanism where fields for one model are stored
in more than one table -- Multi Table Inheritance (also known as MTI).
That's what happens when we do "normal" inheritance of models, without
specifying anything special in the Meta of either of the models.

Python also supports Multiple Inheritance -- one class can have many parent
classes. And this also works with Django's MTI -- we can have multiple MTI.

Usually, when we think of a "core" set of attributes with different extensions,
and we decide to implement it with MTI, we put this core set in a parent
model, and make the extensions subclass it. But in the situation where we
try to break down an existing model, this would mean that code which currently
uses the large model will have to change, to recognize the new parts.

**broken-down-models** puts this idea on its head: The extensions become
parent models, and the core set is defined in a model which inherits them all.
This way, all the fields are still fields of of the model we started with,
for all purposes -- including not just attribute access, but also ORM queries.
For this to really work well, though, some further modifications are required;
this is why the library exists, and it is explained in
`What is really going on here <./EXPLANATIONS.rst>`_

.. The above reference should be done as :ref:`details`


Installation
------------
::

    pip install broken-down-models

Usage
-----
Assume we have a large, central model::

    class Central(models.Model):
        a = models.IntegerField()
        b = models.CharField(max_length=100)
        c = models.DateTimeField()
        # ...
        z = models.IPV4AddressField()

We would like to break it down into groups of fields. Let's say that the first
four fields are really core, useful almost whenever the model is used, but
we want to separate out the others in groups of 5-6. This involves two parts;
the first is

Models
======

As mentioned above, the separate groups are going to be parent classes for the
new ``Central``, so we'll have to define them first. These will be completely
regular models, with one exception: We need to explicitly define their primary
key, and give each of these primary keys a unique name. We can base this name
on the model name; so we'll have something like::

    class Group1(models.Model):
        group1_id = models.IntegerField(primary_key=True)  # New field
        e = models.BooleanField()  # This field is taken from Central
        f = models.TextField()     # This too
        # ...
        j = models.UUIDField(null=True)

Note that we're using an ``IntegerField``, and not an ``AutoField``, for
the primary key; this is because we still assume that objects of this part
of the ``Central`` model will not be created in isolation, but only as part
of a complete ``Central`` object. In such creation, the primary key value
will come from the complete object, and there is no need to generate it for
each of the parts. In fact, an ``AutoField`` should work just as well -- one
is still allowed to set the value of an ``AutoField`` explicitly, and that
is what a ``BrokenDownModel`` will do for its parents behind the scenes.

We'll define similarly the next groups::

    class Group2(models.Model):
        group2_id = models.IntegerField(primary_key=True)
        k = models.BooleanField()
        # ...
        o = models.ForeignKey(SomeOtherModel, null=True, on_delete=models.CASCADE)

    # and Group3, and...

    class Group4(models.Model):
        group4_id = models.IntegerField(primary_key=True)
        # ...
        z = models.IPV4AddressField()

Now we can finally re-define the original model. We'll need to import some
names from the library::

    from bdmodels.fields import VirtualParentLink
    from bdmodels.models import BrokenDownModel

and then::

    class Central(BrokenDownModel, Group1, Group2, Group3, Group4):
        # Add an explicit PK here too
        id = models.AutoField(primary_key=True)

        # Add links to the parents
        group1_ptr = VirtualParentLink(Group1)
        group2_ptr = VirtualParentLink(Group2)
        group3_ptr = VirtualParentLink(Group3)
        group4_ptr = VirtualParentLink(Group4)

        # The original core fields we decided to leave in the model
        a = models.IntegerField()
        b = models.CharField(max_length=100)
        c = models.DateTimeField()
        d = models.DateField()

Note that we had to define the primary key explicitly here as well. This is because
Django's default behavior for MTI is to use the parent-link to the first parent as
the PK of the child. We do not want this.

The ``VirtualPrentLink`` fields defined explicitly replace similarly-named
``OneToOneField`` which Django would generate, by default, to connect a child
model with its MTI parents. They differ from such fields by all using the ``id``
column in the database -- regular parent-link ``OneToOneField`` fields would each define
their own column, although for our use case these columns would all be holding
the same value (same as ``id``).

With these definitions, our app is essentially ready to work against a database where
the ``Central`` model has been broken down (up to some limitations, see below). But we
still have to bring our database to this state. It is now time to talk about...

Migrations
==========

.. note:: TODO: explain migrations and migration_ops

.. note:: TODO: Explain VirtualOneToOneField and VirtualForeignKey

.. note:: TODO: Limitations

  The first and obvious limitation is that we only handle objects accessed
  through the ORM, of course; raw SQL queries will not be magically adapted.

  Another is that if you have custom managers (as is likely on a central model),
  you now have to make them subclass ``bdmodels.models.BrokenDownManager`` instead
  of ``django.db.models.Manager``.

Project TODO
------------

#. It seems like ``VirtualForeignKey`` and ``VirtualOneToOneField`` are problematic
   if their ``from_field`` is not the primary key. Add tests to cover these cases,
   find and document the exact problems and preferably solve them.
#. Activate the tests copied from Django
#. Consider more tests to take from Django, related to FKs and 1to1s.
#. Add tests for bulk-create:

   #. Correctness if the DB backend ``can_return_ids_from_bulk_insert``
   #. Proper failure otherwise

Open-Source Release TODO
----

#. Complete documentation
#. Set License
