"""
apps/documents/tests/test_models.py

Unit and integration tests for the EmployeeDocument model.

Categories covered (per Section 7 of the Technical Requirement Document):
  - Model Tests: constraints, computed properties, __str__, soft delete
  - Integration Tests: tenant isolation, queryset filtering

Markers:
  @pytest.mark.unit         — single function/class, no DB or network I/O
  @pytest.mark.integration  — multiple components, DB, services

All tests use fixtures from conftest.py. Do not use Model.objects.create()
directly — use fixtures instead.
"""

from __future__ import annotations

from datetime import date

import pytest

from apps.documents.choices import DocumentType
from apps.documents.models import EmployeeDocument
from apps.employees.models import Employee

# =============================================================================
# __str__ / field defaults
# =============================================================================


@pytest.mark.unit
def test_document_str(document: EmployeeDocument) -> None:
    """__str__ returns 'DisplayType — emp_number'."""
    assert str(document) == f"KTP — {document.employee.emp_number}"


@pytest.mark.unit
def test_document_default_doc_type(employee: Employee) -> None:
    """doc_type defaults to OTHER when not specified."""
    doc = EmployeeDocument(employee=employee, file_name="misc.pdf")
    assert doc.doc_type == DocumentType.OTHER


@pytest.mark.unit
def test_document_default_is_verified_false(employee: Employee) -> None:
    """is_verified defaults to False."""
    doc = EmployeeDocument(employee=employee, file_name="misc.pdf")
    assert doc.is_verified is False


@pytest.mark.unit
def test_document_default_is_active_true(employee: Employee) -> None:
    """is_active defaults to True (soft-delete flag)."""
    doc = EmployeeDocument(employee=employee, file_name="misc.pdf")
    assert doc.is_active is True


@pytest.mark.unit
def test_document_file_url_blank_by_default(employee: Employee) -> None:
    """file_url defaults to an empty string, never null."""
    doc = EmployeeDocument(employee=employee, file_name="misc.pdf")
    assert doc.file_url == ""


# =============================================================================
# Soft delete — deactivate() / restore()
# =============================================================================


@pytest.mark.integration
def test_deactivate_sets_is_active_false(document: EmployeeDocument) -> None:
    """deactivate() flips is_active to False and stamps deleted_at."""
    document.deactivate()
    assert document.is_active is False
    assert document.deleted_at is not None


@pytest.mark.integration
def test_restore_sets_is_active_true(inactive_document: EmployeeDocument) -> None:
    """restore() flips is_active back to True and clears deleted_at."""
    inactive_document.restore()
    assert inactive_document.is_active is True
    assert inactive_document.deleted_at is None


# =============================================================================
# Manager / QuerySet — for_company, for_employee, alive, verified
# =============================================================================


@pytest.mark.integration
def test_for_company_scopes_to_employee_company(
    document: EmployeeDocument, document_other_company: EmployeeDocument
) -> None:
    """for_company() only returns documents whose employee belongs to that company."""
    company_id = document.employee.company_id
    results = EmployeeDocument.objects.for_company(company_id)
    assert document in results
    assert document_other_company not in results


@pytest.mark.integration
def test_for_employee_filters_to_single_employee(
    two_documents: tuple[EmployeeDocument, EmployeeDocument], employee: Employee
) -> None:
    """for_employee() returns only documents belonging to that employee."""
    doc1, doc2 = two_documents
    results = EmployeeDocument.objects.for_employee(employee.id)
    assert doc1 in results
    assert doc2 in results


@pytest.mark.integration
def test_alive_excludes_soft_deleted(
    document: EmployeeDocument, inactive_document: EmployeeDocument
) -> None:
    """alive() excludes soft-deleted documents."""
    results = EmployeeDocument.objects.alive()
    assert document in results
    assert inactive_document not in results


@pytest.mark.integration
def test_verified_filters_to_verified_only(
    document: EmployeeDocument, verified_document: EmployeeDocument
) -> None:
    """verified() only returns documents with is_verified=True."""
    results = EmployeeDocument.objects.verified()
    assert verified_document in results
    assert document not in results


@pytest.mark.integration
def test_cascade_delete_when_employee_deleted(employee: Employee, document: EmployeeDocument) -> None:
    """Deleting the parent Employee cascades to its EmployeeDocuments."""
    doc_id = document.id
    employee.delete()
    assert not EmployeeDocument.objects.filter(pk=doc_id).exists()


@pytest.mark.unit
def test_valid_until_nullable(employee: Employee) -> None:
    """valid_until may be left null (documents without an expiry)."""
    doc = EmployeeDocument.objects.create(
        employee=employee,
        doc_type="ktp",
        file_name="ktp.pdf",
    )
    assert doc.valid_until is None


@pytest.mark.unit
def test_valid_until_accepts_date(employee: Employee) -> None:
    """valid_until stores a date correctly."""
    doc = EmployeeDocument.objects.create(
        employee=employee,
        doc_type="sim",
        file_name="sim.pdf",
        valid_until=date(2027, 5, 1),
    )
    assert doc.valid_until == date(2027, 5, 1)
