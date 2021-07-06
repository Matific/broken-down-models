Optimizing Queries
==================

Breaking down a model is a trade-off: The main table will become smaller,
queries which use or reference only the "core" fields are likely to become
faster; but code which uses fields outside of the core can become much slower,
and even trigger the infamous "1+N" behavior -- processing a set of objects,
which were all selected in one query before the breaking-down refactoring, may
now require an additional query-per-object, if it involves fetching a field
that has been moved out to a parent.

The library provides tools to overcome this -- we can use
:py:meth:`select_related()
<bdmodels.models.BrokenDownQuerySet.select_related>` to make specific queries
join-in specific parents, or even :py:meth:`fetch_all_parents()
<bdmodels.models.BrokenDownQuerySet.fetch_all_parents>` to join all of them;
but in a large project, how can we find the places where this is needed?

Generally
---------

`nplusone`_ is a library for detecting query inefficiencies in Python ORMs,
which supports the Django ORM. In general, testing your code with this library
can help you detect cases where your code is making 1+N queries. However, it
is written for the typical case, where the problem is caused by following
Foreign Keys. The way we set things up here, 1+N queries are caused by
accessing previously-deferred fields, which are not necessarily Foreign Keys;
`nplusone`_ cannot detect these.

While working on broken-down-models, we added to `nplusone`_ the feature of
detecting instances of 1+N created by accessing deferred fields. Sadly, it
seems that the original library is abandoned, and our pull-requests to improve
it are not likely to be merged. But `our fork`_ is out there for your use.

.. _nplusone: https://pypi.org/project/nplusone/
.. _`our fork`: https://github.com/SlateScience/nplusone/tree/feature/deferred-fields

Besides detecting more cases, this fork also adds a ``TraceNotifier`` which
can be used to get reports with tracebacks when running your test-suite.

To do this, modify your ``manage.py`` as follows:

#. Add relevant imports::

    from nplusone.core import profiler, notifiers
    import nplusone.ext.django  # noqa -- required for profilers

#. Define a Profiler class, similar to this::

    class Profiler(profiler.Profiler):
        def __init__(self, whitelist=None):
            from nplusone.ext.django.middleware import DjangoRule
            self.whitelist = [
                DjangoRule(**item)
                for item in (whitelist or [])
            ]

            self.notifier = notifiers.TraceNotifier(
	        {'NPLUSONE_LOG_LEVEL': logging.WARN}
            )

        def notify(self, message):
            if not message.match(self.whitelist):
                self.notifier.notify(message)

#. Apply the profiler to management command execution; replace the default

   ::

    execute_from_command_line(sys.argv)

   with::

    with Profiler():
        execute_from_command_line(sys.argv)
    

With this, every potential case of 1+N queries will be logged with a
full stack-trace, so you can find exactly where it comes from.

If it's the User model
----------------------

``request.user`` is often used in all sort of ways, and a broken-down
user-model will, by default, cause many queries to be triggered for
the acting user in the views -- and, because it is placed in the
request before your view gets control, you cannot fix these with code
in the view.

If most of the uses of ``request.user`` only touch the core attributes, then
that is fine. But if not, you may want to make sure that ``request.user`` is
fetched with all the parts. If so, there's two (kinds of) places to take care
of:

One is the fetching of users for authentication; django.contrib.auth
uses, for this::

        user = UserModel._default_manager.get_by_natural_key(username)

Since the other common use for ``get_by_natural_key()`` is for the
``loaddata`` and ``dumpdata`` commands, which deal with serialization,
and where the whole user object is required as well, it makes sense to
override the User model's default manager's ``get_by_natural_key()``
with something like::

    def get_by_natural_key(self, username):
        return self.fetch_all_parents().get(**{self.model.USERNAME_FIELD: username})


The other is the code that fetches the user for the request when
they're already logged in; this is "a kind of place" -- the
``get_user()`` method of authentication backends. The canonical
example is of course django.contrib.auth.backends.ModelBackend, whose
method reads::

    def get_user(self, user_id):
        try:
            user = UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None

For broken-down user models, you may prefer a backend with something like::

    def get_user(self, user_id):
        """Overridden for BrokenDownModel support; used for fetching the request user"""
        user_manager = UserModel._default_manager.fetch_all_parents()
        try:
            user = user_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None
