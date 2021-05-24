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
model. The change imagined is an open-heart surgery on a large project.
Maybe, if we look the other way, it won't bother us too much...

**broken-down-models** is here to help you. This is a library which can
help you refactor your large model into a set of smaller ones, each with
its own database table, while most of your project code remains unchanged.

General Idea
------------

Django already includes a mechanism where fields for one model are stored in
more than one table -- Multi Table Inheritance. That's what happens when we
do "normal" inheritance of models, without specifying anything special in
the Meta of either of the models.

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

#. Add proper documentation (even just a README) instead of this file
