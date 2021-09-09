"""
This module, while technically containing tests, is not here for testing
correctness, but rather for profiling. Thus, it is set up to be skipped
in normal testing.

In order to make these tests execute, set the environment variable
PROFILING to some non-empty value. It is then recommended to run
only these tests -- e.g.

    python manage.py test testapp.test_profile

Test methods in this module are decorated with @profile -- the decorator itself
is also defined here, for now. It causes the decorated method to write a file
named after it (with a ".prof" suffix). These files may then be loaded by the
pstats.Stats class from the standard library, for analysis, e.g:

    from pstats import Stats
    stats = Stats('test_save_new_object.prof')

See https://docs.python.org/3/library/profile.html#the-stats-class
"""
import functools
from os import environ
from unittest import SkipTest

from cProfile import Profile

from django.test import TestCase

from .models import Child


def setUpModule():
    if not environ.get('PROFILING'):
        raise SkipTest('This module is only for profiling')


def profile(method):
    @functools.wraps(method)
    def mthd(*args, **kwargs):
        p = Profile()
        p.enable()
        try:
            return method(*args, **kwargs)
        finally:
            p.disable()
            p.dump_stats(f'{method.__name__}.prof')

    return mthd


class ObjectUpdatePerformanceTestCase(TestCase):
    def setUp(self) -> None:
        self.child = Child(para_name='A', parb_name='B', parc_name='C', parc_zit=True)

    @profile
    def test_save_new_object(self):
        N = 200
        for i in range(1, N+1):
            self.child.pk = None
            self.child.child_name = f'Xerxes {i:3}'
            self.child.save()
        self.assertEqual(Child.objects.all().count(), N)

    @profile
    def test_update_full_object(self):
        N = 200
        for i in range(1, N+1):
            self.child.child_name = f'Xerxes {i:3}'
            self.child.save()
        self.assertEqual(Child.objects.all().count(), 1)

    @profile
    def test_update_partial_object(self):
        self.child.child_name = 'Yudhistira'
        self.child.save()
        c = Child.objects.get(child_name='Yudhistira')
        N = 200
        for i in range(1, N+1):
            c.child_name = f'Xerxes {i:3}'
            c.save()
        self.assertEqual(Child.objects.all().count(), 1)

    @profile
    def test_update_partial_parent(self):
        self.child.child_name = 'Yudhistira'
        self.child.save()
        c = Child.objects.get(child_name='Yudhistira')
        N = 200
        for i in range(1, N+1):
            c.para_name = f'Xerxes {i:3}'
            c.save()
        self.assertEqual(Child.objects.all().count(), 1)

    @profile
    def test_update_partial_parent_fields(self):
        self.child.child_name = 'Yudhistira'
        self.child.save()
        c = Child.objects.get(child_name='Yudhistira')
        N = 200
        for i in range(1, N+1):
            c.para_name = f'Xerxes {i:3}'
            c.save(update_fields=['para_name'])
        self.assertEqual(Child.objects.all().count(), 1)
