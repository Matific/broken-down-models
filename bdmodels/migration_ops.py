"""
Migration operations for virtual fields used in broken-down models
"""
from django.db import migrations
from django.db.migrations.operations.base import Operation


# This function is named to look like other migration operations
# noinspection PyPep8Naming
def AddVirtualField(*, model_name, name, field):
    state_operations = [migrations.AddField(model_name=model_name, name=name, field=field, preserve_default=False)]
    database_operations = []
    if field.db_constraint:
        # When a constraints.References is available, we can do something here
        raise NotImplementedError("Constraints for virtual fields not implemented yet "
                                  "(no support for independent REFERENCES constraints)")
    return migrations.SeparateDatabaseAndState(database_operations, state_operations)


class CopyDataToPartial(Operation):
    # For simplicity, we assume both models are in the same app

    atomic = True

    def __init__(self, full_model_name: str, part_model_name: str, elidable: bool = True):
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
