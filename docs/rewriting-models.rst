Rewriting Models
================

.. note:: This continues the example defined in :doc:`the previous page
          <./usage>`.

As mentioned previously, the separate groups are going to be parent classes for
the new ``Central``, so we'll have to define them first. These will be
completely regular models, with one exception: We need to explicitly define
their primary key, and give each of these primary keys a unique name. We can
base this name on the model name; so we'll have something like::

    class Group1(models.Model):
        group1_id = models.IntegerField(primary_key=True)  # New field
        e = models.BooleanField()  # This field is taken from Central
        f = models.TextField()     # This too
        # ...
        j = models.UUIDField(null=True)

Note that we're using an :py:class:`IntegerField
<django.db.models.IntegerField>`, and not an :py:class:`AutoField
<django.db.models.AutoField>`, for the primary key; this is because we still
assume that objects of this part of the ``Central`` model will not be created in
isolation, but only as part of a complete ``Central`` object. In such creation,
the primary key value will come from the complete object, and there is no need
to generate it for each of the parts. In fact, an :py:class:`AutoField
<django.db.models.AutoField>` should work just as well -- one is still allowed
to set the value of an :py:class:`AutoField <django.db.models.AutoField>`
explicitly, and that is what a :py:class:`BrokenDownModel
<bdmodels.models.BrokenDownModel>` will do for its parents behind the scenes.

We'll define similarly the next groups::

    class Group2(models.Model):
        group2_id = models.IntegerField(primary_key=True)
        k = models.BooleanField()
        # ...
        o = models.ForeignKey(SomeOtherModel, null=True, on_delete=models.CASCADE)

    # and Group3, and...

    class Group4(models.Model):
        group4_id = models.IntegerField(primary_key=True)
        # ...
        z = models.IPV4AddressField()

Now we can finally re-define the original model. We'll need to import some names
from the library::

    from bdmodels.fields import VirtualParentLink
    from bdmodels.models import BrokenDownModel

and then::

    class Central(BrokenDownModel, Group1, Group2, Group3, Group4):
        # Add an explicit PK here too
        id = models.AutoField(primary_key=True)

        # Add links to the parents
        group1_ptr = VirtualParentLink(Group1)
        group2_ptr = VirtualParentLink(Group2)
        group3_ptr = VirtualParentLink(Group3)
        group4_ptr = VirtualParentLink(Group4)

        # The original core fields we decided to leave in the model
        a = models.IntegerField()
        b = models.CharField(max_length=100)
        c = models.DateTimeField()
        d = models.DateField()

Note that we had to define the primary key explicitly here as well. This is
because Django's default behavior for MTI is to use the parent-link to the first
parent as the PK of the child. We do not want this.

The :py:class:`VirtualPrentLink <bdmodels.fields.VirtualPrentLink>` fields
defined explicitly, replace similarly-named :py:class:`OneToOneField
<django.db.models.OneToOneField>` fields which Django would generate, by
default, to connect a child model with its MTI parents.  They differ from such
fields by all using the ``id`` column in the database -- regular parent-link
:py:class:`OneToOneField <django.db.models.OneToOneField>` fields would each
define their own column, although for our use case these columns would all be
holding the same value (same as ``id``).

With these definitions, our app is essentially ready to work against a database
where the ``Central`` model has been broken down (up to some limitations, see
below). But we still have to bring our database to this state. It is now time to
talk about...

