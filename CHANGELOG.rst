Release History
===============


0.3.0 (in development)
+++++

Supported versions
------------------

* Add support for upcoming Django 4.1 (and testing against main)
* Add testing with Python 3.10
* Drop support for Django 2.2.x, 3.1.x (both out of support by Django project)
* Drop testing against Python 3.7 to simplify test matrix

API
---

* Optional arguments were added to the ``bulk_create()`` queryset method in
  order to conform with Django 4.1 API. The update-on-conflict functionality
  they define is not yet supported, though.

0.2.1
+++++

Supported versions
------------------

* Add support for Django 4.0

  (only needed to update tests and documentation)



0.2.0
++++++++++++++++++++++

Performance
-----------

* Make save() skip unnecessary parents

Internal
--------

* Add tests for profiling

Documentation
-------------

* Document some limitations
* Add this change-log
* Add some details for contributors
* Add benchmarks

0.1.0 - Initial Release
+++++++++++++++++++++++
