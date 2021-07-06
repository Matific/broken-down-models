bdmodels package
================

bdmodels.models
---------------

.. py:module:: bdmodels.models

.. autoclass:: BrokenDownModel
   :show-inheritance:
	     
   .. automethod:: refresh_from_db
   .. automethod:: getattr_if_loaded

.. autoclass:: BrokenDownManager

.. autoclass:: BrokenDownQuerySet
   :show-inheritance:

   .. automethod:: select_related
   .. automethod:: fetch_all_parents
   .. automethod:: bulk_create


bdmodels.fields
---------------

.. py:module:: bdmodels.fields

.. autoclass:: VirtualForeignKey
   :show-inheritance:

.. autoclass:: VirtualOneToOneField
   :show-inheritance:

.. autoclass:: VirtualParentLink
   :show-inheritance:


bdmodels.migration\_ops
-----------------------

.. py:module:: bdmodels.migration_ops
	       
.. autofunction:: AddVirtualField

.. autoclass:: CopyDataToPartial
