# Generated by Django 2.2.23 on 2021-07-07 15:35

from django.db import migrations

from bdmodels import migration_ops


class Migration(migrations.Migration):

    dependencies = [
        ('testmigs', '0002_break_big_model'),
    ]

    operations = [
        migration_ops.CopyDataToPartial(
            full_model_name='BigModel',
            part_model_name="Partial",
        )
    ]