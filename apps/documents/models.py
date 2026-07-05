"""
apps/documents/models.py

EmployeeDocument — concrete stub, not yet fully implemented.

EmployeeDocument is defined in docs/database-schema.md but not yet fully implemented.
This stub creates the database table so the app has a real migration and can be
built upon incrementally. Will FK to Employee (not yet created).
"""

from django.db import models

from apps.shared.mixins.soft_delete import SoftDeleteMixin
from apps.shared.mixins.timestamped import TimestampedModel


class EmployeeDocument(SoftDeleteMixin, TimestampedModel):
    """
    Represents a document attached to an Employee.

    Stub — EmployeeDocument model is not yet fully implemented.
    Will include: employee FK, doc_type, file_url, file_name, valid_until, is_verified.
    """

    doc_type = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "documents_employee_document"

    def __str__(self) -> str:
        raise NotImplementedError("EmployeeDocument model is not yet fully implemented.")
