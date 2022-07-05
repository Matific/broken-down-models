========================
Using Broken-Down-Models
========================

Installation
------------
No surprises here::

    pip install broken-down-models

You do not need to add anything to ``INSTALLED_APPS`` or any other Django
setting.

Requirements
............

Broken-Down-Models is tested against CPython 3.8, 3.9 and 3.10, with
Django 3.2, 4.0 and 4.1 (and the tip of the ``main`` branch),
using PostgreSQL and SQLite.

When using SQLite, Some migration operations require SQLite >= 3.3.0.  See
:py:class:`CopyDataToPartial <bdmodels.migration_ops.CopyDataToPartial>` for
details -- as far as we're aware, that is also the main hurdle to using
the library with MySQL, Oracle, or any other DBMS (and like any good
hurdle, hopping over it is not hard).


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
four fields are really core, useful almost whenever the model is used, but we
want to separate out the others in groups of 5-6. We will rebuild the model as a
set of related models.

When we are done, the ``Central`` model will have only five columns in its
table -- the four chosen fields, and ``id``. Each of the other groups of fields
will have their own model and be stored in their own table. The behavior of ORM
queries will be changed, but (up to fringe limitations, see below) the
changes will only affect performance, not semantics:

- For queries that just refer to the model (using any of the fields), Django
  will arrange the necessary joins for us behind the scenes.

- Queries that fetch ``Central`` objects will, by default, only bring in the
  core fields; the rest of the fields will be :py:meth:`deferred
  <django:django.db.models.query.QuerySet.defer>` -- that is, the field value
  will be loaded from the database only when it is accessed, much like the way a
  :py:class:`ForeignKey <django.db.models.ForeignKey>` is handled.

  This deferral is special, though: If any of the fields in a group is accessed,
  the whole group will be fetched.

Limitations
...........
There is one obvious and hard limitation: We only handle objects accessed
through the ORM, of course; raw SQL queries will not be magically adapted.

The library makes internal calls to :py:meth:`QuerySet.only()
<django.db.models.query.QuerySet.only>`; user calls to ``only()`` or
``defer()`` on querysets of broken-down models may interact with these
calls in surprising ways.

The library does not handle the database constraints that should be imposed
between a model and its broken-out components.

Updating model fields with values based on other fields using ``F()``-expressions
does not work across MTI relations -- this is a Django limitation; see Django
tickets 30044_, 33091_ and 25643_. When breaking down a model with this library,
one may cause working code to break over this: If the code performs an update
using ``F()``-expressions, and one of the relevant fields is moved to a parent
model, then after the change, the code will run into the Django issues.

.. _30044: https://code.djangoproject.com/ticket/30044
.. _33091: https://code.djangoproject.com/ticket/33091
.. _25643: https://code.djangoproject.com/ticket/25643

Bulk creation for models with multi-table inheritance is not yet supported
by Django. This library provides a partial implementation, so common uses
of ``bulk_create()`` should continue to work after breaking a model down.
However, updating on conflict (as is supported in Django>=4.1) is not
supported.

The Refactoring Process
.......................

The rewrite process involves two required steps -- rewriting the models, and
providing migrations -- and a recommended step of optimizing queries. The next
pages describe each of these in detail.
