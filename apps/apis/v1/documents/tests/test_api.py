"""
apps/apis/v1/documents/tests/test_api.py

Feature tests for the EmployeeDocument API.

Covers:
  - API Tests: full HTTP request/response cycle for every endpoint
  - Permission Tests: role x action x company combinations
  - Tenant Isolation Tests: cross-company data protection
  - Negative Tests: denied permissions, invalid payloads, business-rule violations

Markers:
  @pytest.mark.feature  — full HTTP request/response cycle via DRF APIClient
"""

from __future__ import annotations

import pytest
from rest_framework import status

pytestmark = pytest.mark.feature


def assert_error_response(
    response,
    *,
    expected_status: int,
    expected_error: str | None = None,
    details_has_keys: list[str] | None = None,
) -> None:
    """Assert a response matches the Nexus standard error envelope."""
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got {response.status_code}. "
        f"Response: {response.json()}"
    )
    data = response.json()
    if expected_error:
        assert data.get("error") == expected_error, (
            f"Expected error '{expected_error}', got '{data.get('error')}'"
        )
    if details_has_keys:
        for key in details_has_keys:
            assert key in data.get("details", {}), (
                f"Expected details to contain key '{key}', got {data.get('details')}"
            )


# =============================================================================
# GET /api/v1/employees/{id}/documents/ — List
# =============================================================================


class TestDocumentList:
    """Permission: IsOwnerOrHRAdmin."""

    def test_list_returns_paginated_response(self, hr_admin_client, employee, document) -> None:
        """HR Admin can list an employee's documents."""
        response = hr_admin_client.get(f"/api/v1/employees/{employee.id}/documents/")
        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert "count" in payload
        assert "results" in payload
        assert payload["count"] >= 1

    def test_list_excludes_soft_deleted(self, hr_admin_client, employee, document, inactive_document) -> None:
        """Soft-deleted documents are excluded from the list."""
        response = hr_admin_client.get(f"/api/v1/employees/{employee.id}/documents/")
        results = response.json()["results"]
        returned_ids = {r["id"] for r in results}
        assert str(document.id) in returned_ids
        assert str(inactive_document.id) not in returned_ids

    def test_list_never_exposes_file_url(self, hr_admin_client, employee, document) -> None:
        """Raw storage key (file_url) is never present in the response."""
        response = hr_admin_client.get(f"/api/v1/employees/{employee.id}/documents/")
        results = response.json()["results"]
        assert all("file_url" not in r for r in results)

    def test_list_own_documents_allowed_for_owner(
        self, employee_client, employee_with_user, document_for_linked_employee
    ) -> None:
        """A plain employee can list their own documents."""
        response = employee_client.get(f"/api/v1/employees/{employee_with_user.id}/documents/")
        assert response.status_code == status.HTTP_200_OK

    def test_list_other_employees_documents_denied_for_plain_employee(
        self, employee_client, employee, document
    ) -> None:
        """A plain employee cannot list another employee's documents."""
        response = employee_client.get(f"/api/v1/employees/{employee.id}/documents/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_unauthenticated_returns_401(self, api_client, employee) -> None:
        """Unauthenticated requests are rejected with 401."""
        response = api_client.get(f"/api/v1/employees/{employee.id}/documents/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_cross_company_employee_returns_403(
        self, other_company_client, employee
    ) -> None:
        """Requesting documents for an employee in another company returns 403, not 404."""
        response = other_company_client.get(f"/api/v1/employees/{employee.id}/documents/")
        assert_error_response(response, expected_status=status.HTTP_403_FORBIDDEN)


# =============================================================================
# POST /api/v1/employees/{id}/documents/ — Upload
# =============================================================================


class TestDocumentCreate:
    """Permission: IsHRAdmin."""

    def test_upload_document_succeeds(self, hr_admin_client, employee, uploaded_file) -> None:
        """HR Admin can upload a document with metadata."""
        response = hr_admin_client.post(
            f"/api/v1/employees/{employee.id}/documents/",
            data={"file": uploaded_file, "doc_type": "ktp"},
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()["data"]
        assert data["doc_type"] == "ktp"
        assert data["file_name"] == "ktp-scan.pdf"
        assert "file_url" not in data

    def test_upload_returns_data_envelope(self, hr_admin_client, employee, uploaded_file) -> None:
        """POST /documents/ returns {"data": {...}}."""
        response = hr_admin_client.post(
            f"/api/v1/employees/{employee.id}/documents/",
            data={"file": uploaded_file, "doc_type": "npwp"},
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "data" in data
        assert "id" in data["data"]

    def test_upload_defaults_doc_type_to_other(self, hr_admin_client, employee, uploaded_file) -> None:
        """doc_type defaults to 'other' when not provided."""
        response = hr_admin_client.post(
            f"/api/v1/employees/{employee.id}/documents/",
            data={"file": uploaded_file},
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["data"]["doc_type"] == "other"

    def test_upload_missing_file_returns_400(self, hr_admin_client, employee) -> None:
        """Missing file returns 400 validation error."""
        response = hr_admin_client.post(
            f"/api/v1/employees/{employee.id}/documents/",
            data={"doc_type": "ktp"},
            format="multipart",
        )
        assert_error_response(
            response,
            expected_status=status.HTTP_400_BAD_REQUEST,
            expected_error="validation_error",
            details_has_keys=["file"],
        )

    def test_upload_invalid_doc_type_returns_400(self, hr_admin_client, employee, uploaded_file) -> None:
        """Invalid doc_type returns 400 validation error."""
        response = hr_admin_client.post(
            f"/api/v1/employees/{employee.id}/documents/",
            data={"file": uploaded_file, "doc_type": "not_a_real_type"},
            format="multipart",
        )
        assert_error_response(
            response,
            expected_status=status.HTTP_400_BAD_REQUEST,
            expected_error="validation_error",
        )

    def test_upload_unauthenticated_returns_401(self, api_client, employee, uploaded_file) -> None:
        """Unauthenticated upload is rejected with 401."""
        response = api_client.post(
            f"/api/v1/employees/{employee.id}/documents/",
            data={"file": uploaded_file, "doc_type": "ktp"},
            format="multipart",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upload_manager_role_returns_403(self, manager_client, employee, uploaded_file) -> None:
        """Manager role cannot upload documents (not HR Admin)."""
        response = manager_client.post(
            f"/api/v1/employees/{employee.id}/documents/",
            data={"file": uploaded_file, "doc_type": "ktp"},
            format="multipart",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_upload_plain_employee_role_returns_403(
        self, employee_client, employee_with_user, uploaded_file
    ) -> None:
        """A plain employee cannot upload documents, even for themself."""
        response = employee_client.post(
            f"/api/v1/employees/{employee_with_user.id}/documents/",
            data={"file": uploaded_file, "doc_type": "ktp"},
            format="multipart",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_upload_cross_company_employee_returns_403(
        self, hr_admin_client, employee_other_company, uploaded_file
    ) -> None:
        """Uploading against another company's employee ID returns 403, not 404."""
        response = hr_admin_client.post(
            f"/api/v1/employees/{employee_other_company.id}/documents/",
            data={"file": uploaded_file, "doc_type": "ktp"},
            format="multipart",
        )
        assert_error_response(response, expected_status=status.HTTP_403_FORBIDDEN)


# =============================================================================
# GET /api/v1/employees/{id}/documents/{doc_id}/ — Retrieve
# =============================================================================


class TestDocumentRetrieve:
    """Permission: IsOwnerOrHRAdmin."""

    def test_retrieve_returns_signed_url(self, hr_admin_client, employee, document) -> None:
        """Retrieve returns a signed_url field (never the raw file_url)."""
        response = hr_admin_client.get(
            f"/api/v1/employees/{employee.id}/documents/{document.id}/"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert "signed_url" in data
        assert "file_url" not in data

    def test_retrieve_own_document_allowed_for_owner(
        self, employee_client, employee_with_user, document_for_linked_employee
    ) -> None:
        """The document's owning employee can retrieve their own document."""
        response = employee_client.get(
            f"/api/v1/employees/{employee_with_user.id}/documents/{document_for_linked_employee.id}/"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_other_employees_document_denied(
        self, employee_client, employee, document
    ) -> None:
        """A plain employee cannot retrieve another employee's document."""
        response = employee_client.get(
            f"/api/v1/employees/{employee.id}/documents/{document.id}/"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_nonexistent_document_returns_404(self, hr_admin_client, employee) -> None:
        """A nonexistent document ID returns 404."""
        import uuid

        response = hr_admin_client.get(
            f"/api/v1/employees/{employee.id}/documents/{uuid.uuid4()}/"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_cross_company_document_returns_403(
        self, other_company_client, employee, document
    ) -> None:
        """Retrieving a document scoped to another company returns 403, not 404."""
        response = other_company_client.get(
            f"/api/v1/employees/{employee.id}/documents/{document.id}/"
        )
        assert_error_response(response, expected_status=status.HTTP_403_FORBIDDEN)

    def test_retrieve_unauthenticated_returns_401(self, api_client, employee, document) -> None:
        """Unauthenticated retrieve is rejected with 401."""
        response = api_client.get(
            f"/api/v1/employees/{employee.id}/documents/{document.id}/"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# PATCH /api/v1/employees/{id}/documents/{doc_id}/ — Update metadata
# =============================================================================


class TestDocumentUpdate:
    """Permission: IsHRAdmin."""

    def test_update_doc_type(self, hr_admin_client, employee, document) -> None:
        """HR Admin can update a document's doc_type."""
        response = hr_admin_client.patch(
            f"/api/v1/employees/{employee.id}/documents/{document.id}/",
            data={"doc_type": "sertifikat"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["doc_type"] == "sertifikat"

    def test_update_is_verified(self, hr_admin_client, employee, document) -> None:
        """HR Admin can mark a document as verified."""
        response = hr_admin_client.patch(
            f"/api/v1/employees/{employee.id}/documents/{document.id}/",
            data={"is_verified": True},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["is_verified"] is True

    def test_update_invalid_doc_type_returns_400(self, hr_admin_client, employee, document) -> None:
        """Invalid doc_type returns 400 validation error."""
        response = hr_admin_client.patch(
            f"/api/v1/employees/{employee.id}/documents/{document.id}/",
            data={"doc_type": "not_a_real_type"},
            format="json",
        )
        assert_error_response(
            response,
            expected_status=status.HTTP_400_BAD_REQUEST,
            expected_error="validation_error",
        )

    def test_update_manager_role_returns_403(self, manager_client, employee, document) -> None:
        """Manager role cannot update documents (not HR Admin)."""
        response = manager_client.patch(
            f"/api/v1/employees/{employee.id}/documents/{document.id}/",
            data={"is_verified": True},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_own_document_denied_for_plain_employee(
        self, employee_client, employee_with_user, document_for_linked_employee
    ) -> None:
        """A plain employee cannot update even their own document's metadata."""
        response = employee_client.patch(
            f"/api/v1/employees/{employee_with_user.id}/documents/{document_for_linked_employee.id}/",
            data={"is_verified": True},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_cross_company_document_returns_403(
        self, other_company_client, employee, document
    ) -> None:
        """Updating a document scoped to another company returns 403, not 404."""
        response = other_company_client.patch(
            f"/api/v1/employees/{employee.id}/documents/{document.id}/",
            data={"is_verified": True},
            format="json",
        )
        assert_error_response(response, expected_status=status.HTTP_403_FORBIDDEN)


# =============================================================================
# DELETE /api/v1/employees/{id}/documents/{doc_id}/ — Soft delete
# =============================================================================


class TestDocumentDestroy:
    """Permission: IsHRAdmin."""

    def test_destroy_soft_deletes_document(self, hr_admin_client, employee, document) -> None:
        """DELETE soft-deletes the document (is_active=False), returns 204."""
        response = hr_admin_client.delete(
            f"/api/v1/employees/{employee.id}/documents/{document.id}/"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        document.refresh_from_db()
        assert document.is_active is False

    def test_destroy_manager_role_returns_403(self, manager_client, employee, document) -> None:
        """Manager role cannot delete documents (not HR Admin)."""
        response = manager_client.delete(
            f"/api/v1/employees/{employee.id}/documents/{document.id}/"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        document.refresh_from_db()
        assert document.is_active is True

    def test_destroy_own_document_denied_for_plain_employee(
        self, employee_client, employee_with_user, document_for_linked_employee
    ) -> None:
        """A plain employee cannot delete even their own document."""
        response = employee_client.delete(
            f"/api/v1/employees/{employee_with_user.id}/documents/{document_for_linked_employee.id}/"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_destroy_cross_company_document_returns_403(
        self, other_company_client, employee, document
    ) -> None:
        """Deleting a document scoped to another company returns 403, not 404."""
        response = other_company_client.delete(
            f"/api/v1/employees/{employee.id}/documents/{document.id}/"
        )
        assert_error_response(response, expected_status=status.HTTP_403_FORBIDDEN)

    def test_destroy_unauthenticated_returns_401(self, api_client, employee, document) -> None:
        """Unauthenticated delete is rejected with 401."""
        response = api_client.delete(
            f"/api/v1/employees/{employee.id}/documents/{document.id}/"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_destroy_nonexistent_document_returns_404(self, hr_admin_client, employee) -> None:
        """Deleting a nonexistent document ID returns 404."""
        import uuid

        response = hr_admin_client.delete(
            f"/api/v1/employees/{employee.id}/documents/{uuid.uuid4()}/"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
