"""
Migration operations for virtual fields used in broken-down models
"""
import warnings

from django.db import migrations
from django.db.models import constraints


# This function is named to look like other migration operations
# noinspection PyPep8Naming
def AddVirtualField(model_name, name, field):
    state_operations = [migrations.AddField(model_name=model_name, name=name, field=field, preserve_default=False)]
    database_operations = []
    if field.db_constraint:
        # When a constraints.References is available, we can do something here
        raise NotImplementedError("Constraints for virtual fields not implemented yet "
                                  "(no support for independent REFERENCES constraints)")
    return migrations.SeparateDatabaseAndState(database_operations, state_operations)
