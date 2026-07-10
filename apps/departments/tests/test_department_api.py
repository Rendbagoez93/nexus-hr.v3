"""
apps/departments/tests/test_department_api.py

Feature tests for Department API endpoints.
Uses APIClient for full HTTP request/response testing.
Write-endpoint negative-path tests included.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from apps.departments.models import Department
from apps.departments.services import DepartmentService


@pytest.mark.feature
class TestDepartmentAPIList:
    def test_list_departments(
        self, db, hr_admin_client: APIClient
    ):
        """GET /api/v1/departments/ returns 200 with paginated list."""
        response = hr_admin_client.get("/api/v1/departments/")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_list_with_parent_filter(
        self, db, hr_admin_client: APIClient
    ):
        """GET /api/v1/departments/?parent_id=<uuid> returns 200 filtered list."""
        user = hr_admin_client.handler._force_user
        parent = DepartmentService.create(
            company_id=user.company_id,
            name="Parent",
            code="PAR",
        )
        DepartmentService.create(
            company_id=user.company_id,
            name="Child",
            code="CHD",
            parent_id=parent.id,
        )
        response = hr_admin_client.get(f"/api/v1/departments/?parent_id={parent.id}")
        assert response.status_code == 200
        data = response.json()["results"]
        assert all(d["parent_id"] == str(parent.id) for d in data)

    def test_list_include_inactive(
        self, db, hr_admin_client: APIClient
    ):
        """GET /api/v1/departments/?is_active=false includes inactive."""
        user = hr_admin_client.handler._force_user
        dept = DepartmentService.create(
            company_id=user.company_id,
            name="ActiveDept",
            code="ACT",
        )
        inactive = DepartmentService.create(
            company_id=user.company_id,
            name="InactiveDept",
            code="INA",
        )
        DepartmentService.soft_delete(inactive.id, user.company_id)
        response = hr_admin_client.get("/api/v1/departments/?is_active=false")
        assert response.status_code == 200
        codes = [d["code"] for d in response.json()["results"]]
        assert "INA" in codes


@pytest.mark.feature
class TestDepartmentAPICreate:
    def test_create_department(
        self, db, hr_admin_client: APIClient
    ):
        """POST /api/v1/departments/ with name+code returns 201."""
        response = hr_admin_client.post(
            "/api/v1/departments/",
            data={"name": "Engineering", "code": "ENG"},
            format="json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Engineering"
        assert data["code"] == "ENG"
        assert data["is_active"] is True

    def test_create_with_parent(
        self, db, hr_admin_client: APIClient
    ):
        """POST with name+code+parent_id returns 201 with parent FK set."""
        user = hr_admin_client.handler._force_user
        parent = DepartmentService.create(
            company_id=user.company_id,
            name="Parent",
            code="PAR",
        )
        response = hr_admin_client.post(
            "/api/v1/departments/",
            data={"name": "Child", "code": "CHD", "parent_id": str(parent.id)},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["parent_id"] == str(parent.id)

    # Negative-path
    def test_create_missing_name(
        self, db, hr_admin_client: APIClient
    ):
        """POST without name returns 400."""
        response = hr_admin_client.post(
            "/api/v1/departments/",
            data={"code": "ENG"},
            format="json",
        )
        assert response.status_code == 400

    def test_create_missing_code(
        self, db, hr_admin_client: APIClient
    ):
        """POST without code returns 400."""
        response = hr_admin_client.post(
            "/api/v1/departments/",
            data={"name": "Engineering"},
            format="json",
        )
        assert response.status_code == 400

    def test_create_duplicate_code(
        self, db, hr_admin_client: APIClient
    ):
        """POST with existing code returns 400 or 409."""
        user = hr_admin_client.handler._force_user
        DepartmentService.create(
            company_id=user.company_id,
            name="Dept A",
            code="DUP",
        )
        response = hr_admin_client.post(
            "/api/v1/departments/",
            data={"name": "Dept B", "code": "DUP"},
            format="json",
        )
        assert response.status_code in (400, 409)

    def test_create_parent_not_found(
        self, db, hr_admin_client: APIClient
    ):
        """POST with non-existent parent_id returns 400/404."""
        response = hr_admin_client.post(
            "/api/v1/departments/",
            data={"name": "Orphan", "code": "ORP", "parent_id": str(uuid4())},
            format="json",
        )
        assert response.status_code in (400, 404)
        assert "parent" in response.json().get("message", "").lower()

    def test_code_uppercase_normalized(
        self, db, hr_admin_client: APIClient
    ):
        """POST with code='eng' saves as 'ENG' in response."""
        response = hr_admin_client.post(
            "/api/v1/departments/",
            data={"name": "Engineering", "code": "eng"},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["code"] == "ENG"


@pytest.mark.feature
class TestDepartmentAPIRetrieve:
    def test_retrieve_department(
        self, db, hr_admin_client: APIClient
    ):
        """GET /api/v1/departments/{id}/ returns 200 with dept data."""
        user = hr_admin_client.handler._force_user
        dept = DepartmentService.create(
            company_id=user.company_id,
            name="Engineering",
            code="ENG",
        )
        response = hr_admin_client.get(f"/api/v1/departments/{dept.id}/")
        assert response.status_code == 200
        assert response.json()["name"] == "Engineering"

    def test_retrieve_not_found(
        self, db, hr_admin_client: APIClient
    ):
        """GET with unknown UUID returns 404."""
        response = hr_admin_client.get(f"/api/v1/departments/{uuid4()}/")
        assert response.status_code == 404


@pytest.mark.feature
class TestDepartmentAPIPartialUpdate:
    def test_partial_update(
        self, db, hr_admin_client: APIClient
    ):
        """PATCH with {name: 'New Name'} returns 200 with updated name."""
        user = hr_admin_client.handler._force_user
        dept = DepartmentService.create(
            company_id=user.company_id,
            name="Old Name",
            code="OLD",
        )
        response = hr_admin_client.patch(
            f"/api/v1/departments/{dept.id}/",
            data={"name": "New Name"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    def test_partial_update_not_found(
        self, db, hr_admin_client: APIClient
    ):
        """PATCH unknown UUID returns 404."""
        response = hr_admin_client.patch(
            f"/api/v1/departments/{uuid4()}/",
            data={"name": "New Name"},
            format="json",
        )
        assert response.status_code == 404


@pytest.mark.feature
class TestDepartmentAPIDelete:
    def test_delete_department(
        self, db, hr_admin_client: APIClient
    ):
        """DELETE /api/v1/departments/{id}/ soft-deletes and returns 204."""
        user = hr_admin_client.handler._force_user
        dept = DepartmentService.create(
            company_id=user.company_id,
            name="To Delete",
            code="DEL",
        )
        response = hr_admin_client.delete(f"/api/v1/departments/{dept.id}/")
        assert response.status_code == 204
        dept.refresh_from_db()
        assert dept.is_active is False

    def test_delete_not_found(
        self, db, hr_admin_client: APIClient
    ):
        """DELETE unknown UUID returns 404."""
        response = hr_admin_client.delete(f"/api/v1/departments/{uuid4()}/")
        assert response.status_code == 404


@pytest.mark.feature
class TestDepartmentAPIRestore:
    def test_restore_department(
        self, db, hr_admin_client: APIClient
    ):
        """POST /api/v1/departments/{id}/restore/ restores and returns 200."""
        user = hr_admin_client.handler._force_user
        dept = DepartmentService.create(
            company_id=user.company_id,
            name="To Restore",
            code="RES",
        )
        DepartmentService.soft_delete(dept.id, user.company_id)
        response = hr_admin_client.post(f"/api/v1/departments/{dept.id}/restore/")
        assert response.status_code == 200
        assert response.json()["is_active"] is True

    def test_restore_not_found(
        self, db, hr_admin_client: APIClient
    ):
        """POST restore/ on active or unknown UUID returns 404."""
        user = hr_admin_client.handler._force_user
        dept = DepartmentService.create(
            company_id=user.company_id,
            name="ActiveDept",
            code="ACT",
        )
        # Active dept
        response = hr_admin_client.post(f"/api/v1/departments/{dept.id}/restore/")
        assert response.status_code == 404
        # Unknown UUID
        response = hr_admin_client.post(f"/api/v1/departments/{uuid4()}/restore/")
        assert response.status_code == 404


@pytest.mark.feature
class TestDepartmentAPITree:
    def test_tree_endpoint(
        self, db, hr_admin_client: APIClient
    ):
        """GET /api/v1/departments/tree/ returns 200 with nested children."""
        user = hr_admin_client.handler._force_user
        parent = DepartmentService.create(
            company_id=user.company_id,
            name="Parent",
            code="PAR",
        )
        DepartmentService.create(
            company_id=user.company_id,
            name="Child",
            code="CHD",
            parent_id=parent.id,
        )
        response = hr_admin_client.get("/api/v1/departments/tree/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        root = next(d for d in data if d["code"] == "PAR")
        assert len(root["children"]) == 1
        assert root["children"][0]["code"] == "CHD"
