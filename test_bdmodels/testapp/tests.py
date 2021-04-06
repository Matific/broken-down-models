from django.test import TestCase

from .models import Child


class TestSelectRelated(TestCase):

    def setUp(self):
        super().setUp()
        Child.objects.create(para_name='A', parb_name='B', parc_name='C', child_name='Xerces')

    def test_parents_not_joined_by_default(self):
        """
        By default, fetching a broken-down model selects only the child fields.
        Accessing parent fields requires further database queries.
        """
        with self.assertNumQueries(4):
            c = Child.objects.get(child_name='Xerces')
            parents = [c.para_name, c.parb_name, c.parc_name]
            self.assertEqual("".join(parents), "ABC")

    def test_field_access_fetches_whole_parent(self):
        """
        When a parent field is accessed for the first time, all the
        fields from that parent (and only them) are fetched with it.
        """
        with self.assertNumQueries(2):
            c = Child.objects.get(child_name='Xerces')
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
            c = Child.objects.select_related('parenta_ptr').get(child_name='Xerces')
            self.assertEqual((c.para_zit, c.para_name), (True, 'A'))
        with self.assertNumQueries(1):
            self.assertIs(c.parb_zit, True)
        with self.assertNumQueries(1):
            self.assertEqual(c.parc_name, 'C')

    def test_select_related_all_direct(self):
        """select_related() with no arguments joins all the parents to the selection"""
        with self.assertNumQueries(1):
            c = Child.objects.select_related().get(child_name='Xerces')
            self.assertEqual((c.para_zit, c.para_name), (True, 'A'))
            self.assertIs(c.parb_zit, True)
            self.assertEqual(c.parc_name, 'C')
