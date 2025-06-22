.. image:: https://github.com/matific/broken-down-models/actions/workflows/tests.yml/badge.svg
   :alt: Test status


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
in more than one table: Multi Table Inheritance (also known as MTI).
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
this is why the library exists, and it is explained in its `documentation`_.

.. _documentation: https://broken-down-models.readthedocs.io/en/latest/
