from django.test import TestCase

from .models import Child


class TestSelectRelated(TestCase):

    def setUp(self):
        super().setUp()
        Child.objects.create(para_name='A', parb_name='B', parc_name='C', child_name='Xerces')

    def test_parents_not_joined_by_default(self):
        with self.assertNumQueries(4):
            c = Child.objects.get(child_name='Xerces')
            parents = [c.para_name, c.parb_name, c.parc_name]
            self.assertEqual("".join(parents), "ABC")

    def test_field_access_fetches_whole_parent(self):
        with self.assertNumQueries(2):
            c = Child.objects.get(child_name='Xerces')
            _ = c.para_zit
        with self.assertNumQueries(0):
            _ = c.para_name
        with self.assertNumQueries(2):
            _ = c.parb_zit
            _ = c.parc_zit
        with self.assertNumQueries(0):
            parents = [c.para_name, c.parb_name, c.parc_name]
            self.assertEqual("".join(parents), "ABC")

    def test_select_related_single_direct(self):
        with self.assertNumQueries(1):
            c = Child.objects.select_related('parenta_ptr').get(child_name='Xerces')
            _ = c.para_zit, c.para_name
        with self.assertNumQueries(1):
            _ = c.parb_zit
        with self.assertNumQueries(1):
            _ = c.parc_name

    def test_select_related_all_direct(self):
        with self.assertNumQueries(1):
            c = Child.objects.select_related().get(child_name='Xerces')
            _ = c.para_zit, c.para_name
            _ = c.parb_zit
            _ = c.parc_name
