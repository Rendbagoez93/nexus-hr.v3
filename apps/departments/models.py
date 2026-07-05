"""
apps/departments/models.py

Department and Position — concrete stubs, not yet fully implemented.

Department and Position are defined in docs/database-schema.md but not yet
fully implemented. These stubs create the database tables so the app has
a real migration and can be built upon incrementally.
"""

from django.db import models

from apps.shared.mixins.soft_delete import SoftDeleteMixin
from apps.shared.mixins.timestamped import TimestampedModel


class Department(SoftDeleteMixin, TimestampedModel):
    """
    Represents a department within a Company.

    Stub — Department model is not yet fully implemented.
    Will include: name, code, parent (self-referencing FK), UniqueConstraint(company, code).
    """

    name = models.CharField(max_length=255)

    class Meta:
        db_table = "departments_department"

    def __str__(self) -> str:
        raise NotImplementedError("Department model is not yet fully implemented.")


class Position(SoftDeleteMixin, TimestampedModel):
    """
    Represents a job position within a Department.

    Stub — Position model is not yet fully implemented.
    Will include: title, level, base_salary_min, base_salary_max, department FK.
    """

    title = models.CharField(max_length=255)

    class Meta:
        db_table = "departments_position"

    def __str__(self) -> str:
        raise NotImplementedError("Position model is not yet fully implemented.")
