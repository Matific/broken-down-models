Project TODO
------------
Migrations:
 - an AddVirtualField operation (just SeparateModelAndState over AddField)
 - Fix deconstruct to remove the unnecessary params (``db_index`` and ``editable``)


General Idea
------------

Django already includes a mechanism where fields for one model are stored in
more than one table -- Multi Table Inheritance. That's what happens when we
do "normal" inheritance of models, without specifying anything special in
the Meta of either of the models.

TODO
----
Complete this file