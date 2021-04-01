import itertools

from django.db import models


def get_field_names_to_fetch(model_set):
    fetched_fields = itertools.chain.from_iterable(
        model._meta.local_concrete_fields for model in model_set
    )
    fetched_field_names = [f.name for f in fetched_fields]
    return fetched_field_names


class BrokenDownQuerySet(models.QuerySet):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._with_parents = frozenset()

    def _clone(self):
        c = super()._clone()
        c._with_parents = self._with_parents
        return c

    def select_related(self, *fields):
        """
        Handle the parent deferrals for select_related
        Note: Of necessity, this means that if a parent is select_related, previous "only"
              is overridden and ignored. We make no effort to distinguish between deferrals
              created manually by the user, and those created automatically to defer parents.
        """
        if fields:
            with_parents = set(self._with_parents)
            for parent, link in self.model._meta.parents.items():
                if parent in with_parents:
                    continue
                ptr_name = link.name
                for field in fields:
                    if field == ptr_name or field.startswith(f'{ptr_name}__'):
                        with_parents.add(parent)
                        break
            this = self.update_fetched_parents(with_parents)
            return super(BrokenDownQuerySet, this).select_related(*fields)
        else:
            return self.select_related_with_all_parents()

    def update_fetched_parents(self, parent_set, *, force_update_deferrals=False):
        """Update the set of fetched parents, and reset the set of deferred fields accordingly"""
        if (not force_update_deferrals) and parent_set == self._with_parents:
            return self

        fetched_field_names = self._get_field_names_to_fetch(parent_set)
        updated = self.only(*fetched_field_names)
        updated._with_parents = frozenset(parent_set)
        return updated
    update_fetched_parents.queryset_only = True

    def _get_field_names_to_fetch(self, parent_set):
        return get_field_names_to_fetch([self.model, *parent_set])

    def select_related_with_all_parents(self):
        updated = self.defer(None)
        updated = super(BrokenDownQuerySet, updated).select_related()
        updated._with_parents = frozenset(self.model._meta.parents.keys())
        return updated


class BrokenDownManager(models.Manager.from_queryset(BrokenDownQuerySet)):
    def get_queryset(self):
        return super().get_queryset().update_fetched_parents({}, force_update_deferrals=True)


class BrokenDownModel(models.Model):

    class Meta:
        abstract = True

    objects = BrokenDownManager()

    def refresh_from_db(self, using=None, fields=None):
        """We're overriding this to make sure fetching any parent attribute fetches the whole parent"""
        if fields:
            opts = self._meta
            parents = set(opts.get_field(name).model for name in fields)
            fields = get_field_names_to_fetch(parents)
        super().refresh_from_db(using, fields)
