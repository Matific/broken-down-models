# Generated manually to demonstrate fetched_parents feature

from django.db import migrations, models
import django.db.models.deletion

import bdmodels.fields
import bdmodels.migration_ops as bdmigrations


class Migration(migrations.Migration):

    dependencies = [
        ('testapp', '0005_childwithvirtualnonparent'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChildWithFetchedParents',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('child_name', models.CharField(max_length=10)),
            ],
            options={
                'abstract': False,
            },
        ),
        bdmigrations.AddVirtualField(
            model_name='childwithfetchedparents',
            name='parenta_ptr',
            field=bdmodels.fields.VirtualOneToOneField(from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentA'),
        ),
        bdmigrations.AddVirtualField(
            model_name='childwithfetchedparents',
            name='parentb_ptr',
            field=bdmodels.fields.VirtualOneToOneField(from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentB'),
        ),
        bdmigrations.AddVirtualField(
            model_name='childwithfetchedparents',
            name='parentc_ptr',
            field=bdmodels.fields.VirtualOneToOneField(from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentC'),
        ),
    ]