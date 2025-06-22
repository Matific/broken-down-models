"""
Migration operations for virtual fields used in broken-down models
"""
from django.db import migrations
from django.db.migrations.operations.base import Operation


# This function is named to look like other migration operations
# noinspection PyPep8Naming
def AddVirtualField(*, model_name: str, name: str, field):
    """
    A thin wrapper -- limit :py:class:`AddField <django.db.migrations.operations.AddField>`
    to act on the model and not on the database.

    :param model_name: The model where the field is to be added
    :param name: The name of the field to be added
    :param field: The (virtual) field to be added
    """
    state_operations = [migrations.AddField(model_name=model_name, name=name, field=field, preserve_default=False)]
    database_operations = []
    if field.db_constraint:
        # When a constraints.References is available, we can do something here
        raise NotImplementedError("Constraints for virtual fields not implemented yet "
                                  "(no support for independent REFERENCES constraints)")
    return migrations.SeparateDatabaseAndState(database_operations, state_operations)


class CopyDataToPartial(Operation):
    """
    A migration operation for moving data from a complete model, to a model which has
    some of the complete model's fields, efficiently.

    This is useful when breaking down a large model to parts.

    This is a data operation -- it moves data, does not change schema; the kind
    of operation typically written as a
    :py:class:`RunPython <django.db.migrations.operations.RunPython>` operation.

    Implementation
        The forwards direction of the operation uses SQL ``INSERT-SELECT``
        to create the rows in the table of the partial model. The backwards side uses ``UPDATE``
        with a join to copy data from the partial model's table into (existing) rows of the
        complete model's table.

    Compatibility
        While ``INSERT-SELECT`` is standard SQL, ``UPDATE`` with a join
        (A.K.A ``UPDATE-FROM``) is not. The library currently uses the PostgreSQL syntax,
        which is also supported by SQLite >= 3.33.0; for this reason, the backwards side
        of this migration operation only works with these database backends. Until this
        is fixed, users who need this operation with other backends can write it as
        a :py:class:`RunSQL <django.db.migrations.operations.RunSQL>` operation.

        The SQLite documentation reviews `support of this feature in different systems`_, see
        there for details.

    .. _`support of this feature in different systems`:
       https://www.sqlite.org/lang_update.html#update_from_in_other_sql_database_engines
    """

    atomic = True

    def __init__(self, full_model_name: str, part_model_name: str, elidable: bool = True):
        """
        :param full_model_name: The name of the full model (which at this point has all the fields)
        :param part_model_name: The name of the partial model (whose fields are a PK and some fields
                                copied from the full model)
        :param elidable: Specifies if this operation can be elided when migrations are squashed
        """
        self.full_model_name = full_model_name
        self.part_model_name = part_model_name
        self.elidable = elidable

    def deconstruct(self):
        kwargs = {
            'full_model_name': self.full_model_name,
            'part_model_name': self.part_model_name,
        }
        if self.elidable is not True:
            kwargs['elidable'] = self.elidable
        return (
            self.__class__.__qualname__,
            [],
            kwargs
        )

    def state_forwards(self, app_label, state):
        # This operation does not affect state
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        full_model = from_state.apps.get_model(app_label, self.full_model_name)
        part_model = from_state.apps.get_model(app_label, self.part_model_name)
        db = schema_editor.connection.alias
        if self.allow_migrate_model(db, part_model):
            context = self._sql_context(full_model, part_model, non_pks_as_assignments=False, qn=schema_editor.quote_name)
            sql = self.COPY_FORWARD_SQL.format(**context)
            schema_editor.execute(sql)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        full_model = from_state.apps.get_model(app_label, self.full_model_name)
        part_model = from_state.apps.get_model(app_label, self.part_model_name)
        db = schema_editor.connection.alias
        if self.allow_migrate_model(db, full_model):
            context = self._sql_context(full_model, part_model, non_pks_as_assignments=True, qn=schema_editor.quote_name)
            sql = self.COPY_BACKWARDS_SQL.format(**context)
            schema_editor.execute(sql)

    COPY_FORWARD_SQL = """
    INSERT INTO {part_table} ({part_pk}, {part_non_pks})
    SELECT {full_pk}, {part_non_pks} FROM {full_table}
    """

    COPY_BACKWARDS_SQL = """
    UPDATE {full_table} as "trg"
    SET {part_non_pk_assignments}
    FROM {part_table} as "src"
    WHERE "trg".{full_pk} = "src".{part_pk}
    """

    @staticmethod
    def _sql_context(full_model, part_model, non_pks_as_assignments, qn):
        full_meta, part_meta = full_model._meta, part_model._meta  # noqa
        context = dict(
            full_table=qn(full_meta.db_table),
            full_pk=qn(full_meta.pk.column),
            part_table=qn(part_meta.db_table),
            part_pk=qn(part_meta.pk.column),
        )
        part_non_pks = (qn(f.column) for f in part_meta.local_concrete_fields if not f.primary_key)
        if non_pks_as_assignments:
            context["part_non_pk_assignments"] = ", ".join(
                f'{fld} = "src".{fld}' for fld in part_non_pks
            )
        else:
            context["part_non_pks"] = ", ".join(part_non_pks)
        return context

    def describe(self):
        return "Raw Python operation"
