from unittest import skipUnless

from django.db import models
from django.test import TestCase
from django.test.utils import isolate_apps

from .models import BrokenDownModel
from .fields import VirtualOneToOneField


class InvalidFieldTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        class Target(models.Model):
            pass
        cls.Target = Target

    def test_editable_arg(self):
        with self.assertRaisesMessage(ValueError, "Virtual field cannot be editable"):
            VirtualOneToOneField(self.Target, 'id', on_delete=models.DO_NOTHING, editable=True)
        with self.assertWarnsMessage(Warning, "Virtual fields cannot be editable, editable=False is redundant"):
            VirtualOneToOneField(self.Target, 'id', on_delete=models.DO_NOTHING, editable=False)

    def test_db_index_arg(self):
        with self.assertRaisesMessage(
                ValueError,
                "Virtual field cannot create an index; add indexing on the concrete field (id) instead"
        ):
            VirtualOneToOneField(self.Target, 'id', on_delete=models.DO_NOTHING, db_index=True)
        with self.assertWarnsMessage(Warning, "Virtual fields cannot have indexes, db_index=False is redundant"):
            VirtualOneToOneField(self.Target, 'id', on_delete=models.DO_NOTHING, db_index=False)

    def test_db_constraint_arg(self):
        with self.assertWarnsMessage(Warning, "Constraints on virtual fields are not implemented yet"):
            VirtualOneToOneField(self.Target, 'id', on_delete=models.DO_NOTHING, db_constraint=True)


@isolate_apps('bdmodels')
class InvalidModelsTestCase(TestCase):

    @classmethod
    def setUpParent(cls):
        """This doesn't work as `setUpTestData()`. apparently the isolate_apps() decorator is applied per-method"""
        class Parent(models.Model):
            parent_id = models.BigAutoField(primary_key=True)
        cls.Parent = Parent

    def test_on_delete_set_null(self):
        self.setUpParent()

        class ChangeOnDeleteChild(BrokenDownModel, self.Parent):
            id = models.AutoField(primary_key=True)
            parent_ptr = VirtualOneToOneField(self.Parent, 'id', parent_link=True, on_delete=models.SET_NULL)

        errors = ChangeOnDeleteChild.check()
        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(error.id, 'bdmodels.E002')
        self.assertEqual(
            error.msg,
            'A shared reference field specifies an on_delete rule which would make it change automatically.'
        )
        self.assertEqual(error.obj.model, ChangeOnDeleteChild)
        self.assertEqual(error.obj.name, 'parent_ptr')

    def test_on_delete_set_default(self):
        self.setUpParent()

        class ChangeOnDeleteChild(BrokenDownModel, self.Parent):
            id = models.AutoField(primary_key=True)
            parent_ptr = VirtualOneToOneField(self.Parent, 'id', parent_link=True, on_delete=models.SET_DEFAULT)

        errors = ChangeOnDeleteChild.check()
        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(error.id, 'bdmodels.E002')
        self.assertEqual(
            error.msg,
            'A shared reference field specifies an on_delete rule which would make it change automatically.'
        )
        self.assertEqual(error.obj.model, ChangeOnDeleteChild)
        self.assertEqual(error.obj.name, 'parent_ptr')

    def test_on_delete_do_nothing(self):
        self.setUpParent()

        class ValidOnDeleteChild(BrokenDownModel, self.Parent):
            id = models.AutoField(primary_key=True)
            parent_ptr = VirtualOneToOneField(self.Parent, 'id', parent_link=True, on_delete=models.DO_NOTHING)

        errors = ValidOnDeleteChild.check()
        self.assertEqual(len(errors), 0)

    def test_on_delete_protect(self):
        self.setUpParent()

        class ValidOnDelete(BrokenDownModel, self.Parent):
            id = models.AutoField(primary_key=True)
            parent_ptr = VirtualOneToOneField(self.Parent, 'id', parent_link=True, on_delete=models.PROTECT)

        errors = ValidOnDelete.check()
        self.assertEqual(len(errors), 0)

    @skipUnless(hasattr(models, 'RESTRICT'), "RESTRICT does not exist in this version of Django")
    def test_on_delete_restrict(self):
        self.setUpParent()

        class ValidOnDeleteChild(BrokenDownModel, self.Parent):
            id = models.AutoField(primary_key=True)
            parent_ptr = VirtualOneToOneField(self.Parent, 'id', parent_link=True, on_delete=models)

        errors = ValidOnDeleteChild.check()
        self.assertEqual(len(errors), 0)

    def test_nonvirtual_parent(self):
        self.setUpParent()

        class NonVirtualChild(BrokenDownModel, self.Parent):
            id = models.AutoField(primary_key=True)

        errors = NonVirtualChild.check()
        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(error.id, 'bdmodels.E003')
        self.assertEqual(error.obj, NonVirtualChild)
        self.assertTrue(error.msg.startswith("Field 'parent_ptr'"))
