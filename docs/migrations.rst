Migrations
==========

.. note:: This continues the example started :doc:`before <./usage>`.

If we go and change an existing model, central to our database, in the ways
discussed in :doc:`Rewriting Models <./rewriting-models>`, we need to change our
database schema accordingly. As usual with Django, we will want to do this using
:doc:`migrations <django:topics/migrations>`.

Regretfully, at the time this is written, there is no way to make Django's
:djadmin:`makemigrations` aware of field or model types requiring special
migration operations, so we will need to do some manual migration editing.

That said, :djadmin:`makemigrations` will still give us a good starting
point, even if it will throw some fits on the way there. If we run it, having
changed the models, some of the changes it sees are additions of
:py:class:`VirtualParentLink <bdmodels.fields.VirtualParentLink>` fields named
``*_ptr`` to the original model. These ``*_ptr`` fields pose a problem to the
automatic migration creator: As far as it understands, these are new
non-nullable fields, and as such, they require a default value; it will ask us
questions like:

.. code-block:: none

 
   You are trying to add a non-nullable field 'group1_ptr' to central without
   a default; we can't do that (the database needs something to populate
   existing rows).

   Please select a fix:
   1) Provide a one-off default now (will be set on all existing rows with a
      null value for this column)
   2) Quit, and let me add a default in models.py
      
   Select an option:

As explained above, these fields will not actually be represented by new columns
in the database, and they do not need a default. But
:djadmin:`makemigrations` cannot know that. To pacify it, we'll just give
it a one-off default of 0, and edit this away later.

.. code-block:: none

   Select an option: 1

   Please enter the default value now, as valid Python
   The datetime and django.utils.timezone modules are available, so you can
   do e.g. timezone.now
   Type 'exit' to exit this prompt  
   >>> 0

With this, :djadmin:`makemigrations` will manage to generate a migration.
It will include the following changes:

- The new parent models are created
- The fields that were moved to parent models are removed from the existing
  model
- The ``id`` field on the existing model is changed to a ``VirtualParentLink``
  (it really isn't, details shortly)
- The ``*_ptr`` ``VirtualParentLink`` fields are added to the existing model


It is interesting to note that migrations do not automatically change the
model's superclass (list), and we will not change it either.

The migrations we want comprise four steps for each of the new parent models:

  1. Create the new parent model.
  2. Add the virtual parent link.
  3. Transfer data from the existing model to the new parent model.
  4. Remove from the existing model the fields that were duplicated on
     the parent.

The definition we provided for the ``id`` field exactly mimics the default
provided by Django; it is there because without it, Django will try to use one
of the parent-link keys as a PK. The generated operation to change it to a
relation is created because Django tends to treat a relation field and the
(usually hidden) ``*_id`` field it relies on as interchangeable; when it sees
new relations which use ``id`` as their base field, it gets confused into
thinking that ``id`` is the relation field. But we know better; we don't want
``id`` changed in any way by the migration, and we will remove this operation.

With all this in mind, we will edit the migration accordingly:

  1. The new parent models are exactly as we need them, leave them be;
     remove the :py:class:`AlterField
     <django.db.migrations.operations.AlterField>` operation against
     the original model's ``id`` field.
     
  2. We want the virtual parent link fields added, but we want them added
     only in the model and not in the database (that is why they are "virtual").
     So, we want to replace the generated operations, which look like::

        migrations.AddField(
            model_name='central',
            name='group1_ptr',
            field=bdmodels.fields.VirtualParentLink(default=0, from_field='id', on_delete=django.db.models.deletion.CASCADE, to='app.Group1'),
            preserve_default=False,
        ),

     with operations that do the right thing. The library provides this
     migration operation, we need to import it::

        from bdmodels import migration_ops

     and then we can use it::

        migration_ops.AddVirtualField(
            model_name='central',
            name='group1_ptr',
            field=bdmodels.fields.VirtualParentLink(from_field='id', on_delete=django.db.models.deletion.CASCADE, to='app.Group1'),
        ),

     Note, that the default was removed from the field, and there is no
     ``preserve_default=False`` argument.

  3. Now we'd like to transfer data from the existing full model to
     the new partial models. It is considered best practice to keep
     data-moving operations in separate migrations, and avoid mixing
     them with schema-changing operations. We'll make a new, empty
     migration to hold this operation:
     
     .. code-block:: shell

	$ ./manage.py makemigrations --empty -n breakdown_copy app

     Usually, data-moving in migrations is done with
     :py:class:`RunPython <django.db.migrations.operations.RunPython>`
     operations running functions which use the Django ORM. However,
     copying what is essentially a whole table efficiently requires
     using the SQL ``INSERT-SELECT`` construct, which is currently not
     supported by the ORM. We could write a :py:class:`RunSQL
     <django.db.migrations.operations.RunSQL>` operation, but the
     library provides its own migration operation which writes the raw
     SQL for us, and even includes the reverse side of the operation.

     As above, we will need to import the library migration
     operations::

        from bdmodels import migration_ops

     Then, we can write concise and clear operations::

        operations = [
            migration_ops.CopyDataToPartial(
                full_model_name='Central',
                part_model_name='Group1',
            ),
	    # ...
        ]

  4. Finally, we can remove the now-redundant fields from the old model. We
     create another empty migration:

     .. code-block:: shell

	$ ./manage.py makemigrations --empty -n breakdown_cleanup app

     and move into it all the :py:class:`RemoveField
     <django.db.migrations.operations.RemoveField>` operations from the
     migration which :djadmin:`makemigrations` made for us.

If we look at it from the angle of the generated migration, we:

  1. Kept the ``CreateModel`` operations;
  2. Removed the ``AlterField`` operation;
  3. Changed the ``AddField`` operations into :py:func:`AddVirtualField
     <bdmodels.migration_ops.AddVirtualField>` operations;
  4. Added a 2\ :sup:`nd` migration with data-copying operations;
  5. Moved the ``RemoveField`` operations to a 3\ :sup:`rd` migration which we
     added.

 
