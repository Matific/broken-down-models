# Generated by Django 2.2.21 on 2021-05-05 13:27

from django.conf import settings
from django.db import migrations, models

from bdmodels import migration_ops, fields as bdfields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('testapp', '0002_add_virtual_parent_links'),
    ]

    operations = [
        migrations.CreateModel(
            name='TimeStampedChild',
            fields=[
                ('created_on', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created on')),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('child_name', models.CharField(max_length=10)),
                ('user', models.ForeignKey(null=True, on_delete=models.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migration_ops.AddVirtualField(
            model_name='timestampedchild',
            name='parenta_ptr',
            field=bdfields.VirtualOneToOneField(from_field='id', on_delete=models.DO_NOTHING, parent_link=True, to='testapp.ParentA'),
        ),
        migration_ops.AddVirtualField(
            model_name='timestampedchild',
            name='parentb_ptr',
            field=bdfields.VirtualOneToOneField(from_field='id', on_delete=models.DO_NOTHING, parent_link=True, to='testapp.ParentB'),
        ),
        migration_ops.AddVirtualField(
            model_name='timestampedchild',
            name='parentc_ptr',
            field=bdfields.VirtualOneToOneField(from_field='id', on_delete=models.DO_NOTHING, parent_link=True, to='testapp.ParentC'),
        ),
    ]
