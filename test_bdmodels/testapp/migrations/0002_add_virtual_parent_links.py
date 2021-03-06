# Generated by Django 2.2.20 on 2021-04-18 10:10

from django.db import migrations
import django.db.models.deletion

import bdmodels.fields
import bdmodels.migration_ops as bdmigrations


class Migration(migrations.Migration):

    dependencies = [
        ('testapp', '0001_initial'),
    ]

    operations = [
        bdmigrations.AddVirtualField(
            model_name='child',
            name='parenta_ptr',
            field=bdmodels.fields.VirtualOneToOneField(from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentA'),
        ),
        bdmigrations.AddVirtualField(
            model_name='child',
            name='parentb_ptr',
            field=bdmodels.fields.VirtualOneToOneField(from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentB'),
        ),
        bdmigrations.AddVirtualField(
            model_name='child',
            name='parentc_ptr',
            field=bdmodels.fields.VirtualOneToOneField(from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentC'),
        ),
        bdmigrations.AddVirtualField(
            model_name='nephew',
            name='parentwithfk_ptr',
            field=bdmodels.fields.VirtualOneToOneField(from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentWithFK'),
        ),
        bdmigrations.AddVirtualField(
            model_name='nephew',
            name='parenta_ptr',
            field=bdmodels.fields.VirtualOneToOneField(from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentA'),
        ),
        bdmigrations.AddVirtualField(
            model_name='userchild',
            name='parenta_ptr',
            field=bdmodels.fields.VirtualOneToOneField(from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentA'),
        ),
        bdmigrations.AddVirtualField(
            model_name='userchild',
            name='parentb_ptr',
            field=bdmodels.fields.VirtualOneToOneField(from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentB'),
        ),
        bdmigrations.AddVirtualField(
            model_name='userchild',
            name='parentc_ptr',
            field=bdmodels.fields.VirtualOneToOneField(from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentC'),
        ),
    ]
