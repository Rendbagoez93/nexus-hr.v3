"""
apps/documents/tests/conftest.py — Fixtures for EmployeeDocument tests.

Re-exports Company/Department/Employee fixtures and authenticated API clients
from apps/employees/tests/conftest.py (pytest only auto-loads conftest from
the test directory and its parents, not sibling sub-trees) so document tests
have a ready-made tenant + employee to attach documents to.

Scope strategy:
  module    — company, department, position (read-only reference data)
  function  — employee, document fixtures (tests create/mutate document data)
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.employees.tests.conftest import (  # noqa: F401
    company,
    department,
    employee,
    employee_client,
    employee_other_company,
    employee_with_user,
    hr_admin_client,
    manager_client,
    other_company_client,
    platform_admin_client,
    position,
)

if TYPE_CHECKING:
    from apps.employees.models import Employee


@pytest.fixture
def uploaded_file() -> SimpleUploadedFile:
    """A small in-memory file for upload tests."""
    return SimpleUploadedFile(
        "ktp-scan.pdf", b"%PDF-1.4 fake content", content_type="application/pdf"
    )


@pytest.fixture
def document(db, employee: "Employee"):
    """An active EmployeeDocument belonging to `employee`."""
    from apps.documents.models import EmployeeDocument

    return EmployeeDocument.objects.create(
        employee=employee,
        doc_type="ktp",
        file_url="documents/test/ktp.pdf",
        file_name="ktp.pdf",
        valid_until=date(2030, 1, 1),
    )


@pytest.fixture
def inactive_document(db, employee: "Employee"):
    """A soft-deleted EmployeeDocument belonging to `employee`."""
    from apps.documents.models import EmployeeDocument

    doc = EmployeeDocument.objects.create(
        employee=employee,
        doc_type="npwp",
        file_url="documents/test/npwp.pdf",
        file_name="npwp.pdf",
    )
    doc.deactivate()
    return doc


@pytest.fixture
def verified_document(db, employee: "Employee"):
    """A verified EmployeeDocument belonging to `employee`."""
    from apps.documents.models import EmployeeDocument

    return EmployeeDocument.objects.create(
        employee=employee,
        doc_type="contract",
        file_url="documents/test/contract.pdf",
        file_name="contract.pdf",
        is_verified=True,
    )


@pytest.fixture
def two_documents(db, employee: "Employee"):
    """Two documents belonging to `employee`, for list/filter tests."""
    from apps.documents.models import EmployeeDocument

    doc1 = EmployeeDocument.objects.create(
        employee=employee,
        doc_type="ktp",
        file_url="documents/test/ktp.pdf",
        file_name="ktp.pdf",
    )
    doc2 = EmployeeDocument.objects.create(
        employee=employee,
        doc_type="sim",
        file_url="documents/test/sim.pdf",
        file_name="sim.pdf",
    )
    return doc1, doc2


@pytest.fixture
def document_other_company(db, employee_other_company: "Employee"):
    """An EmployeeDocument belonging to an employee in a different company."""
    from apps.documents.models import EmployeeDocument

    return EmployeeDocument.objects.create(
        employee=employee_other_company,
        doc_type="contract",
        file_url="documents/other/contract.pdf",
        file_name="contract.pdf",
    )


@pytest.fixture
def document_for_linked_employee(db, employee_with_user: "Employee"):
    """A document owned by the employee linked to an AuthUser (self-service access tests)."""
    from apps.documents.models import EmployeeDocument

    return EmployeeDocument.objects.create(
        employee=employee_with_user,
        doc_type="ktp",
        file_url="documents/linked/ktp.pdf",
        file_name="ktp.pdf",
    )
