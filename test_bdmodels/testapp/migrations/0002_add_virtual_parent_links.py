# Generated by Django 2.2.20 on 2021-04-18 10:10

import bdmodels.fields
from django.db import migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('testapp', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=[
            migrations.AddField(
                model_name='child',
                name='parenta_ptr',
                field=bdmodels.fields.VirtualOneToOneField(db_index=False, editable=False, from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentA'),
                preserve_default=False,
            ),
            migrations.AddField(
                model_name='child',
                name='parentb_ptr',
                field=bdmodels.fields.VirtualOneToOneField(db_index=False, editable=False, from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentB'),
                preserve_default=False,
            ),
            migrations.AddField(
                model_name='child',
                name='parentc_ptr',
                field=bdmodels.fields.VirtualOneToOneField(db_index=False, editable=False, from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentC'),
                preserve_default=False,
            ),
            migrations.AddField(
                model_name='nephew',
                name='parentwithfk_ptr',
                field=bdmodels.fields.VirtualOneToOneField(db_index=False, editable=False, from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentWithFK'),
            ),
            migrations.AddField(
                model_name='nephew',
                name='parenta_ptr',
                field=bdmodels.fields.VirtualOneToOneField(db_index=False, editable=False, from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentA'),
                preserve_default=False,
            ),
            migrations.AddField(
                model_name='userchild',
                name='parenta_ptr',
                field=bdmodels.fields.VirtualOneToOneField(db_index=False, editable=False, from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentA'),
                preserve_default=False,
            ),
            migrations.AddField(
                model_name='userchild',
                name='parentb_ptr',
                field=bdmodels.fields.VirtualOneToOneField(db_index=False, editable=False, from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentB'),
                preserve_default=False,
            ),
            migrations.AddField(
                model_name='userchild',
                name='parentc_ptr',
                field=bdmodels.fields.VirtualOneToOneField(db_index=False, editable=False, from_field='id', on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, to='testapp.ParentC'),
                preserve_default=False,
            ),
        ]),
    ]
