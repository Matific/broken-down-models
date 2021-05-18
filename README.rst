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
#. Add tests for VirtualParentLink
#. Add tests for bulk-create:
    #. Correctness if the DB backend ``can_return_ids_from_bulk_insert``
    #. Proper failure otherwise

Open-Source Release TODO
----

#. Add proper documentation (even just a README) instead of this file
#. Add ``tox`` testing for a range of Python and Django versions
