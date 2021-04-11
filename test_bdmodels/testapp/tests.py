from unittest import expectedFailure

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Child, PartialChild, ParentB, UserChild, Nephew


class SelectRelatedTestCase(TestCase):

    def setUp(self):
        super().setUp()
        Child.objects.create(para_name='A', parb_name='B', parc_name='C', child_name='Xerxes')

    def test_parents_not_joined_by_default(self):
        """
        By default, fetching a broken-down model selects only the child fields.
        Accessing parent fields requires further database queries.
        """
        with self.assertNumQueries(1):
            c = Child.objects.get(child_name='Xerxes')
        with self.assertNumQueries(3):
            parents = [c.para_name, c.parb_name, c.parc_name]
        self.assertEqual("".join(parents), "ABC")

    def test_field_access_fetches_whole_parent(self):
        """
        When a parent field is accessed for the first time, all the
        fields from that parent (and only them) are fetched with it.
        """
        with self.assertNumQueries(2):
            c = Child.objects.get(child_name='Xerxes')
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
            c = Child.objects.select_related('parenta_ptr').get(child_name='Xerxes')
            self.assertEqual((c.para_zit, c.para_name), (True, 'A'))
        with self.assertNumQueries(1):
            self.assertIs(c.parb_zit, True)
        with self.assertNumQueries(1):
            self.assertEqual(c.parc_name, 'C')

    def test_select_related_all_direct(self):
        """select_related() with no arguments joins all the parents to the selection"""
        with self.assertNumQueries(1):
            c = Child.objects.select_related().get(child_name='Xerxes')
            self.assertEqual((c.para_zit, c.para_name), (True, 'A'))
            self.assertIs(c.parb_zit, True)
            self.assertEqual(c.parc_name, 'C')

    def test_select_related_non_parent(self):
        user = get_user_model().objects.create(username='artaxerxes')
        c = Child.objects.get(child_name='Xerxes')
        c.user = user
        c.save()
        with self.assertNumQueries(1):
            cc = Child.objects.select_related('user').get(child_name='Xerxes')
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


class PartialChildTestCase(TestCase):

    def setUp(self):
        super().setUp()
        c = PartialChild.objects.create(
            child_name='Orphan', para_name='A',
        )
        # TODO: reversing the order here causes unexpected behavior where parentc_ptr is not set to null
        # (probably a Django bug)
        c.parentc_ptr.delete()
        c.parentb_ptr.delete()

    def tearDown(self):
        # Make the missing record not missing
        c = PartialChild.objects.get(child_name='Orphan')
        ParentB.objects.create(bid=c.parentb_ptr_id, parb_name='B')

    def test_child_with_missing_parent_null(self):
        """We can create a child object with parents set to null"""
        c = PartialChild.objects.get(child_name='Orphan')
        self.assertEqual(c.para_name, 'A')
        self.assertEqual(c.parentc_ptr_id, None)
        self.assertEqual(c.parc_name, None)

    def test_child_with_notnull_missing_parent_raises_proper_exception(self):
        """We can create a child object with parents set to null"""
        c = PartialChild.objects.get(child_name='Orphan')
        self.assertTrue(c.parentb_ptr_id)
        with self.assertRaises(ParentB.DoesNotExist):
            c.parb_name


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
