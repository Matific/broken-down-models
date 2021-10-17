==========
Benchmarks
==========

.. admonition:: Benchmarks do not reflect your use case

   Always take benchmarks with a grain of salt. The numbers reported here
   should not be taken as a promise or guarantee of any kind; they are
   presented in order to give an indication of the order-of-magnitude of
   results one may achieve. If you use it in your own project, the numbers
   are likely to be different.

This library was used to refactor a model which, indeed, had a table with
43 columns and a few million rows. Five parts were broken out, leaving
a core of 13 columns. To measure performance in conditions that resemble
a production load, we used the following setup:

- Out of measurement, set up a pool of 50K record ids
  
- Start 50 threads. Each thread:
  
  - Gets 100 ids from the pool, at random (for tests which update records,
    the sets of ids for threads are disjoint; otherwise, allow overlaps)
    
  - Performs the test with all its ids
    
- Time until all threads complete.

This was performed on Postgres; first, on the database before break-down,
after ``VACUUM ANALYZE`` on the whole database; then performed the break-down,
``VACUUM FULL`` on the main table, and ran the tests again.

These are the tests we did, and the performance changes we got. Notice that,
as might be expected, some benchmarks deteriorate.


get: +14%
    Fetch each objects, that is ``Model.objects.get(id=id)`` for each id.

get-info: +2%
    Fetch object and access a non-core field. In the broken-down
    case, ``select_related()`` was used.

    We do not consider this change significant.

save-core: +14%
    Fetch each object, change core field and save.

save-core-fields: +7%
    Fetch each object, change core field and save with ``update_fields=``.

save-core-bulk: +8%
    Fetch all objects with ``filter(id__in=ids)``, change a core field
    in each, save using ``bulk_update()``.
    
    With ``bulk_update()`` the specific fields to update are named.

save-non-core: -13%
    Fetch each object, change a non-core field and save.
    In the broken-down case, this implies saving to two tables.

save-non-core-fields: -4%
    Fetch each object, change non-core field and save with ``update_fields=``

save-non-core-bulk: +9%
    Fetch all objects with ``filter(id__in=ids)``, change a non-core field
    in each, save using ``bulk_update()``.
    
    With ``bulk_update()`` the specific fields to update are named.
