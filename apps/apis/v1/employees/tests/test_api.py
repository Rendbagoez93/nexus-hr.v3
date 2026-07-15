"""
apps/apis/v1/employees/tests/test_api.py

Feature tests for the Employee API.

Covers:
  - API Tests: full HTTP request/response cycle for every endpoint
  - Permission Tests: role × action × company combinations
  - Tenant Isolation Tests: cross-company data protection
  - Negative Tests: denied permissions, invalid payloads, business-rule violations

Markers:
  @pytest.mark.feature  — full HTTP request/response cycle via DRF APIClient
"""

from __future__ import annotations

from datetime import date

import pytest
from rest_framework import status

from apps.employees.models import Employee

pytestmark = pytest.mark.feature


# =============================================================================
# Helper assertions
# =============================================================================

def assert_error_response(
    response,
    *,
    expected_status: int,
    expected_error: str | None = None,
    message_contains: str | None = None,
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
    if message_contains:
        assert message_contains.lower() in str(data.get("message", "")).lower(), (
            f"Expected message to contain '{message_contains}', got '{data.get('message')}'"
        )
    if details_has_keys:
        for key in details_has_keys:
            assert key in data.get("details", {}), (
                f"Expected details to contain key '{key}', got {data.get('details')}"
            )


# =============================================================================
# GET /api/v1/employees/ — List
# =============================================================================

class TestEmployeeList:
    """Permission: IsHRAdmin (read access via IsAuthenticated on list)."""

    def test_list_returns_paginated_response(
        self,
        hr_admin_client,
        employee,
    ) -> None:
        """Authenticated HR Admin can list employees."""
        response = hr_admin_client.get("/api/v1/employees/")
        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert "count" in payload
        assert "results" in payload
        assert payload["count"] >= 1

    def test_list_returns_data_envelope_for_single_result(
        self,
        hr_admin_client,
        two_employees,
        department,
    ) -> None:
        """Paginated list uses standard envelope: count/next/previous/results."""
        response = hr_admin_client.get("/api/v1/employees/")
        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert set(payload.keys()) == {"count", "next", "previous", "results"}

    def test_list_filter_by_status(
        self,
        hr_admin_client,
        employee,
        resigned_employee,
    ) -> None:
        """?status=active returns only active employees."""
        response = hr_admin_client.get("/api/v1/employees/", {"status": "active"})
        assert response.status_code == status.HTTP_200_OK
        results = response.json()["results"]
        assert all(r["status"] == "active" for r in results)

    def test_list_filter_by_department(
        self,
        hr_admin_client,
        employee,
        resigned_employee,
    ) -> None:
        """?department_id=X returns employees in that department."""
        dept_id = str(employee.department_id)
        response = hr_admin_client.get("/api/v1/employees/", {"department_id": dept_id})
        assert response.status_code == status.HTTP_200_OK
        results = response.json()["results"]
        assert all(r["department_id"] == dept_id for r in results)

    def test_list_filter_by_is_active(
        self,
        hr_admin_client,
        employee,
        inactive_employee,
    ) -> None:
        """?is_active=true excludes soft-deleted employees."""
        response = hr_admin_client.get("/api/v1/employees/", {"is_active": "true"})
        assert response.status_code == status.HTTP_200_OK
        results = response.json()["results"]
        assert all(r["is_active"] is True for r in results)

    def test_list_invalid_department_uuid(
        self,
        hr_admin_client,
    ) -> None:
        """Non-UUID department_id returns 400 validation error."""
        response = hr_admin_client.get("/api/v1/employees/", {"department_id": "not-a-uuid"})
        assert_error_response(
            response,
            expected_status=status.HTTP_400_BAD_REQUEST,
            expected_error="validation_error",
            details_has_keys=["department_id"],
        )

    def test_list_excludes_other_company_employees(
        self,
        hr_admin_client,
        employee,
        employee_other_company,
    ) -> None:
        """Employees from other companies are not returned."""
        response = hr_admin_client.get("/api/v1/employees/")
        assert response.status_code == status.HTTP_200_OK
        results = response.json()["results"]
        returned_ids = {r["id"] for r in results}
        assert str(employee_other_company.id) not in returned_ids

    def test_list_unauthenticated_returns_401(
        self,
        api_client,
    ) -> None:
        """Unauthenticated requests are rejected with 401."""
        response = api_client.get("/api/v1/employees/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_manager_role_allowed(
        self,
        manager_client,
        employee,
    ) -> None:
        """Manager role can list employees (IsAuthenticated)."""
        response = manager_client.get("/api/v1/employees/")
        assert response.status_code == status.HTTP_200_OK

    def test_list_plain_employee_role_allowed(
        self,
        employee_client,
        employee,
    ) -> None:
        """Plain employee role can list employees (IsAuthenticated)."""
        response = employee_client.get("/api/v1/employees/")
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# POST /api/v1/employees/ — Create
# =============================================================================

class TestEmployeeCreate:
    """Permission: IsHRAdmin."""

    def test_create_minimal_employee(
        self,
        hr_admin_client,
        company,
    ) -> None:
        """HR Admin can create a minimal employee."""
        payload = {
            "first_name": "Jane",
            "last_name": "Create",
            "email": "jane.create@nexus.example.com",
            "join_date": "2024-01-15",
        }
        response = hr_admin_client.post("/api/v1/employees/", data=payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["data"]["first_name"] == "Jane"
        assert data["data"]["last_name"] == "Create"
        assert data["data"]["emp_number"] is not None

    def test_create_full_employee(
        self,
        hr_admin_client,
        company,
        department,
        position,
    ) -> None:
        """HR Admin can create a fully-specified employee."""
        payload = {
            "first_name": "Bob",
            "last_name": "Full",
            "email": "bob.full@nexus.example.com",
            "phone": "081234567890",
            "mobile_phone": "081298765432",
            "gender": "male",
            "date_of_birth": "1992-03-20",
            "place_of_birth": "Bandung",
            "id_card_address": "Jl. Braga No.1, Bandung",
            "residential_address": "Jl. Dago No.2, Bandung",
            "department_id": str(department.id),
            "position_id": str(position.id),
            "status": "active",
            "employment_type": "permanent",
            "join_date": "2024-01-01",
            "base_salary": "15000000.00",
        }
        response = hr_admin_client.post("/api/v1/employees/", data=payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["data"]["department_id"] == str(department.id)
        assert data["data"]["position_id"] == str(position.id)
        assert data["data"]["employment_type"] == "permanent"
        assert data["data"]["base_salary"] == "15000000.00"

    def test_create_employee_with_direct_manager(
        self,
        hr_admin_client,
        company,
        department,
        employee,
    ) -> None:
        """Employee can be created with a direct_manager_id."""
        payload = {
            "first_name": "Junior",
            "last_name": "Reports",
            "email": "junior.reports@nexus.example.com",
            "join_date": "2025-01-01",
            "department_id": str(department.id),
            "direct_manager_id": str(employee.id),
        }
        response = hr_admin_client.post("/api/v1/employees/", data=payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["data"]["direct_manager_id"] == str(employee.id)

    def test_create_returns_data_envelope(
        self,
        hr_admin_client,
        company,
    ) -> None:
        """POST /employees/ returns {"data": {...}}."""
        payload = {
            "first_name": "Data",
            "last_name": "Envelope",
            "email": "data.envelope@nexus.example.com",
            "join_date": "2024-01-01",
        }
        response = hr_admin_client.post("/api/v1/employees/", data=payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "data" in data
        assert "id" in data["data"]
        assert "emp_number" in data["data"]

    def test_create_invalid_email(
        self,
        hr_admin_client,
        company,
    ) -> None:
        """Invalid email returns 400 validation error."""
        payload = {
            "first_name": "Bad",
            "last_name": "Email",
            "email": "not-an-email",
            "join_date": "2024-01-01",
        }
        response = hr_admin_client.post("/api/v1/employees/", data=payload, format="json")
        assert_error_response(
            response,
            expected_status=status.HTTP_400_BAD_REQUEST,
            expected_error="validation_error",
            details_has_keys=["email"],
        )

    def test_create_missing_required_field(
        self,
        hr_admin_client,
        company,
    ) -> None:
        """Missing required fields return 400 validation error."""
        payload = {
            "first_name": "Missing",
            "last_name": "Fields",
            # missing email and join_date
        }
        response = hr_admin_client.post("/api/v1/employees/", data=payload, format="json")
        assert_error_response(
            response,
            expected_status=status.HTTP_400_BAD_REQUEST,
            expected_error="validation_error",
        )

    def test_create_invalid_gender(
        self,
        hr_admin_client,
        company,
    ) -> None:
        """Invalid gender value returns 400 validation error."""
        payload = {
            "first_name": "Bad",
            "last_name": "Gender",
            "email": "bad.gender@nexus.example.com",
            "join_date": "2024-01-01",
            "gender": "invalid_gender",
        }
        response = hr_admin_client.post("/api/v1/employees/", data=payload, format="json")
        assert_error_response(
            response,
            expected_status=status.HTTP_400_BAD_REQUEST,
            expected_error="validation_error",
        )

    def test_create_duplicate_email_same_company(
        self,
        hr_admin_client,
        employee,
    ) -> None:
        """Duplicate email within the same company returns 400."""
        payload = {
            "first_name": "Duplicate",
            "last_name": "Email",
            "email": employee.email,
            "join_date": "2024-01-01",
        }
        response = hr_admin_client.post("/api/v1/employees/", data=payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_invalid_department_id(
        self,
        hr_admin_client,
        company,
    ) -> None:
        """Non-existent department_id returns 404."""
        import uuid
        payload = {
            "first_name": "Bad",
            "last_name": "Dept",
            "email": "bad.dept@nexus.example.com",
            "join_date": "2024-01-01",
            "department_id": str(uuid.uuid4()),
        }
        response = hr_admin_client.post("/api/v1/employees/", data=payload, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_unauthenticated_returns_401(
        self,
        api_client,
        company,
    ) -> None:
        """Unauthenticated create returns 401."""
        payload = {
            "first_name": "Unauth",
            "last_name": "Create",
            "email": "unauth.create@nexus.example.com",
            "join_date": "2024-01-01",
        }
        response = api_client.post("/api/v1/employees/", data=payload, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_manager_role_returns_403(
        self,
        manager_client,
        company,
    ) -> None:
        """Manager role cannot create employees (not HR Admin)."""
        payload = {
            "first_name": "Manager",
            "last_name": "Denied",
            "email": "manager.denied@nexus.example.com",
            "join_date": "2024-01-01",
        }
        response = manager_client.post("/api/v1/employees/", data=payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_plain_employee_role_returns_403(
        self,
        employee_client,
        company,
    ) -> None:
        """Plain employee role cannot create employees."""
        payload = {
            "first_name": "Employee",
            "last_name": "Denied",
            "email": "employee.denied@nexus.example.com",
            "join_date": "2024-01-01",
        }
        response = employee_client.post("/api/v1/employees/", data=payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# GET /api/v1/employees/{id}/ — Retrieve
# =============================================================================

class TestEmployeeRetrieve:
    """Permission: IsOwnerOrHRAdmin."""

    def test_retrieve_as_hr_admin(
        self,
        hr_admin_client,
        employee,
    ) -> None:
        """HR Admin can retrieve any employee in their company."""
        response = hr_admin_client.get(f"/api/v1/employees/{employee.id}/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["id"] == str(employee.id)
        assert data["data"]["first_name"] == employee.first_name

    def test_retrieve_returns_data_envelope(
        self,
        hr_admin_client,
        employee,
    ) -> None:
        """GET /employees/{id}/ returns {"data": {...}}."""
        response = hr_admin_client.get(f"/api/v1/employees/{employee.id}/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "id" in data["data"]

    def test_retrieve_cross_company_returns_403(
        self,
        other_company_client,
        employee,
    ) -> None:
        """Cross-company access returns 403, not 404 (security rule)."""
        response = other_company_client.get(f"/api/v1/employees/{employee.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_nonexistent_id_returns_404(
        self,
        hr_admin_client,
    ) -> None:
        """Non-existent employee ID returns 404."""
        import uuid
        response = hr_admin_client.get(f"/api/v1/employees/{uuid.uuid4()}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_unauthenticated_returns_401(
        self,
        api_client,
        employee,
    ) -> None:
        """Unauthenticated retrieve returns 401."""
        response = api_client.get(f"/api/v1/employees/{employee.id}/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_manager_role_allowed(
        self,
        manager_client,
        employee,
    ) -> None:
        """Manager role can retrieve employees (IsOwnerOrHRAdmin on list)."""
        response = manager_client.get(f"/api/v1/employees/{employee.id}/")
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_plain_employee_role_allowed_for_own_record(
        self,
        employee_client,
        employee_with_user,
    ) -> None:
        """Plain employee can retrieve their own employee record."""
        response = employee_client.get(f"/api/v1/employees/{employee_with_user.id}/")
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_plain_employee_role_denied_for_other_record(
        self,
        employee_client,
        employee,
    ) -> None:
        """Plain employee cannot retrieve another employee's record."""
        response = employee_client.get(f"/api/v1/employees/{employee.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# PATCH /api/v1/employees/{id}/ — Partial Update
# =============================================================================

class TestEmployeePartialUpdate:
    """Permission: IsHRAdmin."""

    def test_update_first_name(
        self,
        hr_admin_client,
        employee,
    ) -> None:
        """HR Admin can update an employee's first_name."""
        response = hr_admin_client.patch(
            f"/api/v1/employees/{employee.id}/",
            data={"first_name": "Johnny"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["first_name"] == "Johnny"

    def test_update_returns_data_envelope(
        self,
        hr_admin_client,
        employee,
    ) -> None:
        """PATCH returns {"data": {...}}."""
        response = hr_admin_client.patch(
            f"/api/v1/employees/{employee.id}/",
            data={"last_name": "Updated"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data

    def test_update_status(
        self,
        hr_admin_client,
        employee,
    ) -> None:
        """HR Admin can update status to 'inactive'."""
        response = hr_admin_client.patch(
            f"/api/v1/employees/{employee.id}/",
            data={"status": "inactive"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["status"] == "inactive"

    def test_update_invalid_status(
        self,
        hr_admin_client,
        employee,
    ) -> None:
        """Invalid status value returns 400 validation error."""
        response = hr_admin_client.patch(
            f"/api/v1/employees/{employee.id}/",
            data={"status": "invalid_status"},
            format="json",
        )
        assert_error_response(
            response,
            expected_status=status.HTTP_400_BAD_REQUEST,
            expected_error="validation_error",
        )

    def test_update_invalid_gender(
        self,
        hr_admin_client,
        employee,
    ) -> None:
        """Invalid gender value returns 400 validation error."""
        response = hr_admin_client.patch(
            f"/api/v1/employees/{employee.id}/",
            data={"gender": "invalid"},
            format="json",
        )
        assert_error_response(
            response,
            expected_status=status.HTTP_400_BAD_REQUEST,
            expected_error="validation_error",
        )

    def test_update_cross_company_returns_403(
        self,
        other_company_client,
        employee,
    ) -> None:
        """Cross-company update returns 403."""
        response = other_company_client.patch(
            f"/api/v1/employees/{employee.id}/",
            data={"first_name": "Hacked"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_nonexistent_returns_404(
        self,
        hr_admin_client,
    ) -> None:
        """Updating non-existent employee returns 404."""
        import uuid
        response = hr_admin_client.patch(
            f"/api/v1/employees/{uuid.uuid4()}/",
            data={"first_name": "Nobody"},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_unauthenticated_returns_401(
        self,
        api_client,
        employee,
    ) -> None:
        """Unauthenticated update returns 401."""
        response = api_client.patch(
            f"/api/v1/employees/{employee.id}/",
            data={"first_name": "Hacker"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_manager_role_returns_403(
        self,
        manager_client,
        employee,
    ) -> None:
        """Manager role cannot update employees."""
        response = manager_client.patch(
            f"/api/v1/employees/{employee.id}/",
            data={"first_name": "Manager Update"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_plain_employee_role_returns_403(
        self,
        employee_client,
        employee,
    ) -> None:
        """Plain employee role cannot update employees."""
        response = employee_client.patch(
            f"/api/v1/employees/{employee.id}/",
            data={"first_name": "Employee Update"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_empty_uuid_field_becomes_null(
        self,
        hr_admin_client,
        employee,
        department,
        position,
    ) -> None:
        """Empty-string department_id is treated as null (clears the field)."""
        # employee has department set via fixture
        assert employee.department_id is not None
        response = hr_admin_client.patch(
            f"/api/v1/employees/{employee.id}/",
            data={"department_id": ""},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["department_id"] is None


# =============================================================================
# POST /api/v1/employees/{id}/deactivate/ — Deactivate
# =============================================================================

class TestEmployeeDeactivate:
    """Permission: IsHRAdmin."""

    def test_deactivate_sets_resigned_status(
        self,
        hr_admin_client,
        employee,
    ) -> None:
        """Deactivate sets status to 'resigned' and records resign_date."""
        response = hr_admin_client.post(
            f"/api/v1/employees/{employee.id}/deactivate/",
            data={"resign_date": "2025-12-31"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Employee deactivated successfully."

        # Verify state change persisted
        employee.refresh_from_db()
        assert employee.status == "resigned"

    def test_deactivate_returns_message_envelope(
        self,
        hr_admin_client,
        employee,
    ) -> None:
        """Deactivate returns {"message": "..."} (action confirmation)."""
        response = hr_admin_client.post(
            f"/api/v1/employees/{employee.id}/deactivate/",
            data={"resign_date": "2025-12-31", "termination_reason": "Retirement"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "Employee deactivated" in data["message"]

    def test_deactivate_requires_resign_date(
        self,
        hr_admin_client,
        employee,
    ) -> None:
        """Omitting resign_date returns 400 validation error."""
        response = hr_admin_client.post(
            f"/api/v1/employees/{employee.id}/deactivate/",
            data={},
            format="json",
        )
        assert_error_response(
            response,
            expected_status=status.HTTP_400_BAD_REQUEST,
            expected_error="validation_error",
        )

    def test_deactivate_already_terminated_returns_400(
        self,
        hr_admin_client,
        terminated_employee,
    ) -> None:
        """Cannot deactivate an already-terminated employee."""
        response = hr_admin_client.post(
            f"/api/v1/employees/{terminated_employee.id}/deactivate/",
            data={"resign_date": "2025-12-31"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_deactivate_cross_company_returns_403(
        self,
        other_company_client,
        employee,
    ) -> None:
        """Cross-company deactivate returns 403."""
        response = other_company_client.post(
            f"/api/v1/employees/{employee.id}/deactivate/",
            data={"resign_date": "2025-12-31"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_deactivate_nonexistent_returns_404(
        self,
        hr_admin_client,
    ) -> None:
        """Deactivating non-existent employee returns 404."""
        import uuid
        response = hr_admin_client.post(
            f"/api/v1/employees/{uuid.uuid4()}/deactivate/",
            data={"resign_date": "2025-12-31"},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_deactivate_unauthenticated_returns_401(
        self,
        api_client,
        employee,
    ) -> None:
        """Unauthenticated deactivate returns 401."""
        response = api_client.post(
            f"/api/v1/employees/{employee.id}/deactivate/",
            data={"resign_date": "2025-12-31"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_deactivate_manager_role_returns_403(
        self,
        manager_client,
        employee,
    ) -> None:
        """Manager role cannot deactivate employees."""
        response = manager_client.post(
            f"/api/v1/employees/{employee.id}/deactivate/",
            data={"resign_date": "2025-12-31"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_deactivate_plain_employee_role_returns_403(
        self,
        employee_client,
        employee,
    ) -> None:
        """Plain employee role cannot deactivate employees."""
        response = employee_client.post(
            f"/api/v1/employees/{employee.id}/deactivate/",
            data={"resign_date": "2025-12-31"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# GET /api/v1/me/ — Self-service profile
# =============================================================================

class TestMeProfile:
    """Permission: Authenticated (any role)."""

    def test_me_returns_own_employee_profile(
        self,
        employee_with_user,
    ) -> None:
        """Employee can retrieve their own profile via /me/."""
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=employee_with_user.user)
        response = client.get("/api/v1/employees/me/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["id"] == str(employee_with_user.id)
        assert data["data"]["email"] == employee_with_user.email

    def test_me_returns_data_envelope(
        self,
        employee_with_user,
    ) -> None:
        """GET /me/ returns {"data": {...}}."""
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=employee_with_user.user)
        response = client.get("/api/v1/employees/me/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data

    def test_me_unauthenticated_returns_401(
        self,
        api_client,
    ) -> None:
        """Unauthenticated /me/ returns 401."""
        response = api_client.get("/api/v1/employees/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_no_employee_profile_returns_404(
        self,
        manager_client,
    ) -> None:
        """User with no linked employee profile gets 404."""
        response = manager_client.get("/api/v1/employees/me/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Tenant isolation — boundary tests
# =============================================================================

class TestTenantIsolation:
    """Verify cross-tenant data protection at the API boundary."""

    def test_list_shows_only_own_company_employees(
        self,
        hr_admin_client,
        employee,
        employee_other_company,
    ) -> None:
        """GET /employees/ never returns employees from other companies."""
        response = hr_admin_client.get("/api/v1/employees/")
        assert response.status_code == status.HTTP_200_OK
        ids = {r["id"] for r in response.json()["results"]}
        assert str(employee_other_company.id) not in ids

    def test_retrieve_cross_company_returns_403(
        self,
        other_company_client,
        employee,
    ) -> None:
        """GET /employees/{id}/ for another company's ID returns 403."""
        response = other_company_client.get(f"/api/v1/employees/{employee.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_cross_company_returns_403(
        self,
        other_company_client,
        employee,
    ) -> None:
        """PATCH /employees/{id}/ for another company's ID returns 403."""
        response = other_company_client.patch(
            f"/api/v1/employees/{employee.id}/",
            data={"first_name": "Hijacked"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_deactivate_cross_company_returns_403(
        self,
        other_company_client,
        employee,
    ) -> None:
        """POST /employees/{id}/deactivate/ for another company's ID returns 403."""
        response = other_company_client.post(
            f"/api/v1/employees/{employee.id}/deactivate/",
            data={"resign_date": "2025-12-31"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_department_filter_respects_tenant_boundary(
        self,
        hr_admin_client,
        company,
        department,
        employee_other_company,
    ) -> None:
        """Filtering by department_id never leaks cross-tenant employees."""
        # Filter by a department that belongs to hr_admin's company
        response = hr_admin_client.get(
            "/api/v1/employees/",
            {"department_id": str(department.id)},
        )
        assert response.status_code == status.HTTP_200_OK
        results = response.json()["results"]
        # No employee from other_company should appear
        other_company_emp_ids = {str(employee_other_company.id)}
        assert other_company_emp_ids.isdisjoint({r["id"] for r in results})

    def test_invalid_department_id_in_filter_returns_empty(
        self,
        hr_admin_client,
        employee,
    ) -> None:
        """Filtering by a department that doesn't exist returns empty (not all employees)."""
        import uuid
        fake_dept_id = str(uuid.uuid4())
        response = hr_admin_client.get(
            "/api/v1/employees/",
            {"department_id": fake_dept_id},
        )
        assert response.status_code == status.HTTP_200_OK
        # Should return empty because the department doesn't belong to this company
        assert response.json()["count"] == 0
