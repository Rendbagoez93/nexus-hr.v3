"""
apps/documents/models.py

EmployeeDocument — files/metadata attached to an Employee record
(KTP, NPWP, employment contract, ijazah, SIM, certificates, etc).

EmployeeDocument has no company FK of its own — tenant scoping is derived
through employee.company, matching docs/database-schema.md
(documents_employee_document) where the only owning FK is `employee`.
"""

import uuid

from django.db import models

from apps.documents.choices import DocumentType
from apps.employees.models import Employee
from apps.shared.mixins.soft_delete import SoftDeleteMixin
from apps.shared.mixins.timestamped import TimestampedModel


class EmployeeDocumentQuerySet(models.QuerySet):
    """QuerySet for EmployeeDocument, tenant-scoped via employee.company."""

    def for_company(self, company_id) -> "EmployeeDocumentQuerySet":
        return self.filter(employee__company_id=company_id)

    def for_employee(self, employee_id) -> "EmployeeDocumentQuerySet":
        return self.filter(employee_id=employee_id)

    def alive(self) -> "EmployeeDocumentQuerySet":
        return self.filter(is_active=True)

    def verified(self) -> "EmployeeDocumentQuerySet":
        return self.filter(is_verified=True)


class EmployeeDocumentManager(models.Manager):
    """Custom manager for EmployeeDocument — scoped through employee.company."""

    def get_queryset(self) -> EmployeeDocumentQuerySet:
        return EmployeeDocumentQuerySet(self.model, using=self._db)

    def for_company(self, company_id) -> EmployeeDocumentQuerySet:
        return self.get_queryset().for_company(company_id)

    def for_employee(self, employee_id) -> EmployeeDocumentQuerySet:
        return self.get_queryset().for_employee(employee_id)

    def alive(self) -> EmployeeDocumentQuerySet:
        return self.get_queryset().alive()

    def verified(self) -> EmployeeDocumentQuerySet:
        return self.get_queryset().verified()


class EmployeeDocument(SoftDeleteMixin, TimestampedModel):
    """
    A document (KTP, NPWP, employment contract, certificate, etc.) attached
    to an Employee.

    Files live privately in S3/MinIO — `file_url` stores only the storage
    key, never a publicly-reachable URL. Always serve clients a short-lived
    pre-signed URL via ``apps.shared.utils.storage.generate_signed_url``,
    never this raw field.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="documents",
        db_index=True,
    )
    doc_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
    )
    file_url = models.CharField(max_length=512, blank=True, default="")
    file_name = models.CharField(max_length=255, blank=True, default="")
    valid_until = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    objects = EmployeeDocumentManager()

    class Meta:
        db_table = "documents_employee_document"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["employee", "doc_type"],
                name="idx_empdoc_employee_type",
            ),
            models.Index(
                fields=["employee", "is_active"],
                name="idx_empdoc_employee_active",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_doc_type_display()} — {self.employee.emp_number}"
