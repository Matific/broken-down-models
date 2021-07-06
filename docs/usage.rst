========================
Using Broken-Down-Models
========================

Installation
------------
No surprises here::

    pip install broken-down-models

You do not need to add anything to ``INSTALLED_APPS`` or any other Django
setting.

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

The Refactoring Process
.......................

The rewrite process involves two required steps -- rewriting the models, and
providing migrations -- and a recommended step of optimizing queries. The next
pages describe each of these in detail.
