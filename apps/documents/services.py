"""
apps/documents/services.py

Business logic for EmployeeDocument operations.

EmployeeDocument has no company FK of its own — tenant isolation is enforced
through the parent Employee record (EmployeeService.get_by_id raises 403 for
cross-company access, 404 when the employee genuinely doesn't exist).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, BinaryIO

from django.db import transaction

from apps.documents.choices import DocumentType
from apps.documents.exceptions import DocumentError
from apps.documents.models import EmployeeDocument
from apps.documents.selectors import DocumentSelector
from apps.employees.services.employee_service import EmployeeService
from apps.shared.utils.storage import generate_document_upload_key, generate_signed_url, upload_file

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID


class DocumentService:
    """Handles EmployeeDocument operations for a given employee/company."""

    @staticmethod
    def list_for_employee(employee_id: UUID, company_id: UUID):
        """List active documents for an employee, enforcing tenant boundary."""
        EmployeeService.get_by_id(employee_id, company_id)
        return DocumentSelector.for_employee(employee_id, company_id)

    @staticmethod
    def get_by_id(pk: UUID, employee_id: UUID, company_id: UUID) -> EmployeeDocument:
        """
        Fetch a single document, enforcing employee + company boundary.

        Raises 403 when the document exists but belongs to another company,
        so cross-tenant requests never confirm or deny existence.
        """
        EmployeeService.get_by_id(employee_id, company_id)
        try:
            return (
                EmployeeDocument.objects.for_company(company_id)
                .for_employee(employee_id)
                .select_related("employee")
                .get(pk=pk)
            )
        except EmployeeDocument.DoesNotExist:
            if (
                EmployeeDocument.objects.filter(pk=pk)
                .exclude(employee__company_id=company_id)
                .exists()
            ):
                raise DocumentError(
                    detail="You do not have access to this document.",
                    status_code=403,
                )
            raise DocumentError(detail="Document not found.", status_code=404)

    @staticmethod
    def get_signed_url(document: EmployeeDocument) -> str:
        """Generate a short-lived (15-minute) signed URL for a document's file."""
        if not document.file_url:
            return ""
        return generate_signed_url(document.file_url)

    @staticmethod
    @transaction.atomic
    def upload(
        employee_id: UUID,
        company_id: UUID,
        file_obj: BinaryIO,
        file_name: str,
        doc_type: str = DocumentType.OTHER,
        valid_until: date | None = None,
    ) -> EmployeeDocument:
        """Upload a file to private storage and create the EmployeeDocument record."""
        employee = EmployeeService.get_by_id(employee_id, company_id)

        key = generate_document_upload_key(
            company_id=str(company_id),
            employee_id=str(employee_id),
            filename=file_name,
        )
        content_type = getattr(file_obj, "content_type", None)
        stored_key = upload_file(file_obj, key, content_type=content_type)

        return EmployeeDocument.objects.create(
            employee=employee,
            doc_type=doc_type,
            file_url=stored_key,
            file_name=file_name,
            valid_until=valid_until,
        )

    @staticmethod
    @transaction.atomic
    def update(pk: UUID, employee_id: UUID, company_id: UUID, **fields) -> EmployeeDocument:
        """Update a document's metadata (doc_type, valid_until, is_verified)."""
        document = DocumentService.get_by_id(pk, employee_id, company_id)
        for field_name, value in fields.items():
            setattr(document, field_name, value)
        document.save()
        return document

    @staticmethod
    @transaction.atomic
    def soft_delete(pk: UUID, employee_id: UUID, company_id: UUID) -> EmployeeDocument:
        """Soft-delete a document. The underlying stored file is left in place."""
        document = DocumentService.get_by_id(pk, employee_id, company_id)
        document.deactivate()
        return document
