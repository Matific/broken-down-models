from django.core.management import call_command
from django.db import connection
from django.test import TransactionTestCase

from .models import BigModel


class BasicMigrationsTestCase(TransactionTestCase):

    def tearDown(self):
        call_command('migrate')

    def test_backwards_migrations(self):
        alo = BigModel.objects.create(a=True, b=False, c=1, d="aloha")
        bye = BigModel.objects.create(a=False, b=True, c=2, d="bye")
        call_command('migrate', 'testmigs', '0001_initial')
        crsr = connection.cursor()
        for broken in (alo, bye):
            # Cannot use BigModel.objects.raw() here because that apparently doesn't support MTI properly
            crsr.execute('select id, a, b, c, d from testmigs_bigmodel where id=%s', params=[broken.id])
            row = crsr.fetchone()
            rowd = dict(zip((col[0] for col in crsr.description), row))
            big = BigModel(**rowd)
            self.assertEqual(big.id, broken.id)
            self.assertEqual(big.a, broken.a)
            self.assertEqual(big.b, broken.b)
            self.assertEqual(big.c, broken.c)
            self.assertEqual(big.d, broken.d)

    def test_forwards_migrations(self):
        alo = BigModel.objects.create(a=True, b=False, c=1, d="aloha")
        bye = BigModel.objects.create(a=False, b=True, c=2, d="bye")
        call_command('migrate', 'testmigs', '0001_initial')
        ciao = dict(id=17, a=False, b=None, c=17, d="ciao")
        dasv = dict(id=18, a=False, b=None, c=0, d="dasvedanya")
        cursor = connection.cursor()
        for record in (ciao, dasv):
            cursor.execute(
                'insert into testmigs_bigmodel ("id", "a", "b", "c", "d")'
                ' values(%s, %s, %s, %s, %s)',
                params=[record[fld] for fld in "id a b c d".split()],
            )
        call_command('migrate', 'testmigs')
        for obj in (alo, bye):
            fetched = BigModel.objects.get(pk=obj.pk)
            self.assertEqual(fetched.id, fetched.partial_id)
            self.assertTrue(all(
                getattr(obj, fld) == getattr(fetched, fld)
                for fld in "id a b c d".split()
            ))
        for record in (ciao, dasv):
            fetched = BigModel.objects.get(pk=record['id'])
            self.assertEqual(fetched.id, fetched.partial_id)
            self.assertTrue(all(
                record[fld] == getattr(fetched, fld)
                for fld in "id a b c d".split()
            ))

