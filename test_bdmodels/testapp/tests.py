from unittest import expectedFailure, skipUnless

from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.test.utils import isolate_apps

from bdmodels.fields import VirtualOneToOneField
from .models import BrokenDownModel, Child, UserChild, Nephew


class SelectRelatedTestCase(TestCase):

    ChildClass = Child

    def setUp(self):
        super().setUp()
        self.ChildClass.objects.create(para_name='A', parb_name='B', parc_name='C', child_name='Xerxes')

    def test_parents_not_joined_by_default(self):
        """
        By default, fetching a broken-down model selects only the child fields.
        Accessing parent fields requires further database queries.
        """
        with self.assertNumQueries(1):
            c = self.ChildClass.objects.get(child_name='Xerxes')
        with self.assertNumQueries(3):
            parents = [c.para_name, c.parb_name, c.parc_name]
        self.assertEqual("".join(parents), "ABC")

    def test_field_access_fetches_whole_parent(self):
        """
        When a parent field is accessed for the first time, all the
        fields from that parent (and only them) are fetched with it.
        """
        with self.assertNumQueries(2):
            c = self.ChildClass.objects.get(child_name='Xerxes')
            self.assertIs(c.para_zit, True)
        with self.assertNumQueries(0):
            self.assertEqual(c.para_name, 'A')
        with self.assertNumQueries(2):
            self.assertIs(c.parb_zit, True)
            self.assertIs(c.parc_zit, True)
        with self.assertNumQueries(0):
            parents = [c.para_name, c.parb_name, c.parc_name]
            self.assertEqual("".join(parents), "ABC")

    def test_select_related_single_direct(self):
        """select_related() with a single, immediate parent link, joins the parent to the selection"""
        with self.assertNumQueries(1):
            c = self.ChildClass.objects.select_related('parenta_ptr').get(child_name='Xerxes')
            self.assertEqual((c.para_zit, c.para_name), (True, 'A'))
        with self.assertNumQueries(1):
            self.assertIs(c.parb_zit, True)
        with self.assertNumQueries(1):
            self.assertEqual(c.parc_name, 'C')

    def test_select_related_all_direct(self):
        """select_related() with no arguments joins all the parents to the selection"""
        with self.assertNumQueries(1):
            c = self.ChildClass.objects.select_related().get(child_name='Xerxes')
            self.assertEqual((c.para_zit, c.para_name), (True, 'A'))
            self.assertIs(c.parb_zit, True)
            self.assertEqual(c.parc_name, 'C')

    def test_select_related_non_parent(self):
        user = get_user_model().objects.create(username='artaxerxes')
        c = self.ChildClass.objects.get(child_name='Xerxes')
        c.user = user
        c.save()
        with self.assertNumQueries(1):
            cc = self.ChildClass.objects.select_related('user').get(child_name='Xerxes')
            self.assertEqual(cc.user.username, 'artaxerxes')


class UserChildTestCase(TestCase):

    def setUp(self):
        super().setUp()
        user = get_user_model().objects.create(username='artaxerxes')
        UserChild.objects.create(para_name='A', parb_name='B', parc_name='C', child_name='Xerxes', user=user)

    def test_select_related_non_parent(self):
        with self.assertNumQueries(1):
            uc = UserChild.objects.select_related('user').get(child_name='Xerxes')
            self.assertEqual(uc.user.username, 'artaxerxes')
        with self.assertNumQueries(1):
            # Note: We can do this with UserChild, it doesn't work with Child because its
            # FK to User is nullable and the empty select_related() doesn't collect nullable FKs.
            uc = UserChild.objects.select_related().get(child_name='Xerxes')
            self.assertEqual(uc.user.username, 'artaxerxes')


@isolate_apps('testapp')
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


class UncleTestCase(TestCase):
    def test_select_related_through_parent(self):
        user = get_user_model().objects.create(username='artaxerxes')
        child = Nephew.objects.create(parfk_user=user)
        with self.assertNumQueries(1):
            c = Nephew.objects.select_related('parfk_user').get(pk=child.pk)
            self.assertEqual(c.parfk_user.username, 'artaxerxes')

    @expectedFailure
    def test_select_related_through_parent_with_id(self):
        """
        select-related through a parent has a subtle failure: it brings the related object and sets
        the FK field to it, but it doesn't set the related *_id field. Consequently, if the id field
        is accessed directly, it is fetched -- and in fact, even throws away the already-fetched
        related object. Thus, the assertEqual() line belows, which we expect to perform no queries,
        actually performs two -- one to get the parfk_user_id field, and then one to get
        the parfk_user object, even though we already had it.
        """
        user = get_user_model().objects.create(username='artaxerxes')
        child = Nephew.objects.create(parfk_user=user)
        with self.assertNumQueries(1):
            c = Nephew.objects.select_related('parfk_user').get(pk=child.pk)
            self.assertEqual(c.parfk_user_id, c.parfk_user.id)
