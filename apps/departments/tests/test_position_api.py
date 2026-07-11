"""
apps/departments/tests/test_position_api.py

Feature tests for Position API endpoints.
Uses APIClient for full HTTP request/response testing.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from apps.departments.models import Department
from apps.departments.services import PositionService


@pytest.mark.feature
class TestPositionAPIList:
    def test_list_positions(
        self, db, hr_admin_client: APIClient
    ):
        """GET /api/v1/positions/ returns 200 with paginated list."""
        response = hr_admin_client.get("/api/v1/positions/")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_list_with_department_filter(
        self, db, hr_admin_client: APIClient
    ):
        """GET /api/v1/positions/?department_id=<uuid> returns 200 filtered list."""
        user = hr_admin_client.handler._force_user
        dept = Department.objects.create(
            company_id=user.company_id,
            name="Filter Dept",
            code="FLT",
        )
        PositionService.create(
            company_id=user.company_id,
            department_id=dept.id,
            title="Filtered Pos",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        response = hr_admin_client.get(f"/api/v1/positions/?department_id={dept.id}")
        assert response.status_code == 200
        data = response.json()["results"]
        assert all(p["department_id"] == str(dept.id) for p in data)

    def test_list_with_level_filter(
        self, db, hr_admin_client: APIClient
    ):
        """GET /api/v1/positions/?level=manager returns 200 filtered list."""
        user = hr_admin_client.handler._force_user
        dept = Department.objects.create(
            company_id=user.company_id,
            name="Level Dept",
            code="LVL",
        )
        PositionService.create(
            company_id=user.company_id,
            department_id=dept.id,
            title="Manager Pos",
            level="manager",
            base_salary_min=Decimal("10000000"),
            base_salary_max=Decimal("15000000"),
        )
        PositionService.create(
            company_id=user.company_id,
            department_id=dept.id,
            title="Staff Pos",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        response = hr_admin_client.get("/api/v1/positions/?level=manager")
        assert response.status_code == 200
        data = response.json()["results"]
        assert all(p["level"] == "manager" for p in data)


@pytest.mark.feature
class TestPositionAPICreate:
    def test_create_position(
        self, db, hr_admin_client: APIClient
    ):
        """POST /api/v1/positions/ with full payload returns 201."""
        user = hr_admin_client.handler._force_user
        dept = Department.objects.create(
            company_id=user.company_id,
            name="Create Dept",
            code="CRT",
        )
        response = hr_admin_client.post(
            "/api/v1/positions/",
            data={
                "department_id": str(dept.id),
                "title": "Software Engineer",
                "level": "staff",
                "base_salary_min": "5000000",
                "base_salary_max": "8000000",
            },
            format="json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Software Engineer"
        assert data["level"] == "staff"

    # Negative-path
    def test_create_missing_department_id(
        self, db, hr_admin_client: APIClient
    ):
        """POST without department_id returns 400."""
        response = hr_admin_client.post(
            "/api/v1/positions/",
            data={
                "title": "No Dept",
                "level": "staff",
                "base_salary_min": "5000000",
                "base_salary_max": "8000000",
            },
            format="json",
        )
        assert response.status_code == 400

    def test_create_missing_title(
        self, db, hr_admin_client: APIClient
    ):
        """POST without title returns 400."""
        user = hr_admin_client.handler._force_user
        dept = Department.objects.create(
            company_id=user.company_id,
            name="Title Dept",
            code="TTL",
        )
        response = hr_admin_client.post(
            "/api/v1/positions/",
            data={
                "department_id": str(dept.id),
                "level": "staff",
                "base_salary_min": "5000000",
                "base_salary_max": "8000000",
            },
            format="json",
        )
        assert response.status_code == 400

    def test_create_salary_min_greater_than_max(
        self, db, hr_admin_client: APIClient
    ):
        """Pydantic validator rejects min > max with 400."""
        user = hr_admin_client.handler._force_user
        dept = Department.objects.create(
            company_id=user.company_id,
            name="Salary Dept",
            code="SAL",
        )
        response = hr_admin_client.post(
            "/api/v1/positions/",
            data={
                "department_id": str(dept.id),
                "title": "Bad Range",
                "level": "staff",
                "base_salary_min": "10000000",
                "base_salary_max": "5000000",
            },
            format="json",
        )
        assert response.status_code == 400

    def test_create_department_not_found(
        self, db, hr_admin_client: APIClient
    ):
        """POST with non-existent department_id returns 400/404."""
        response = hr_admin_client.post(
            "/api/v1/positions/",
            data={
                "department_id": str(uuid4()),
                "title": "Orphan",
                "level": "staff",
                "base_salary_min": "5000000",
                "base_salary_max": "8000000",
            },
            format="json",
        )
        assert response.status_code in (400, 404)


@pytest.mark.feature
class TestPositionAPIRetrieve:
    def test_retrieve_position(
        self, db, hr_admin_client: APIClient
    ):
        """GET /api/v1/positions/{id}/ returns 200."""
        user = hr_admin_client.handler._force_user
        dept = Department.objects.create(
            company_id=user.company_id,
            name="Ret Dept",
            code="RET",
        )
        pos = PositionService.create(
            company_id=user.company_id,
            department_id=dept.id,
            title="Retrieve Me",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        response = hr_admin_client.get(f"/api/v1/positions/{pos.id}/")
        assert response.status_code == 200
        assert response.json()["title"] == "Retrieve Me"

    def test_retrieve_not_found(
        self, db, hr_admin_client: APIClient
    ):
        """GET unknown UUID returns 404."""
        response = hr_admin_client.get(f"/api/v1/positions/{uuid4()}/")
        assert response.status_code == 404


@pytest.mark.feature
class TestPositionAPIPartialUpdate:
    def test_partial_update(
        self, db, hr_admin_client: APIClient
    ):
        """PATCH with {title: '...'} returns 200."""
        user = hr_admin_client.handler._force_user
        dept = Department.objects.create(
            company_id=user.company_id,
            name="Patch Dept",
            code="PTCH",
        )
        pos = PositionService.create(
            company_id=user.company_id,
            department_id=dept.id,
            title="Old Title",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        response = hr_admin_client.patch(
            f"/api/v1/positions/{pos.id}/",
            data={"title": "New Title"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["title"] == "New Title"

    def test_update_salary_breach(
        self, db, hr_admin_client: APIClient
    ):
        """new min > existing max returns 400."""
        user = hr_admin_client.handler._force_user
        dept = Department.objects.create(
            company_id=user.company_id,
            name="Breach Dept",
            code="BRCH",
        )
        pos = PositionService.create(
            company_id=user.company_id,
            department_id=dept.id,
            title="Breach Test",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        response = hr_admin_client.patch(
            f"/api/v1/positions/{pos.id}/",
            data={"base_salary_min": "15000000"},
            format="json",
        )
        assert response.status_code == 400

    def test_update_department_wrong_company(
        self, db, hr_admin_client: APIClient
    ):
        """PATCH with dept from other company returns 400/404."""
        user = hr_admin_client.handler._force_user
        dept = Department.objects.create(
            company_id=user.company_id,
            name="Own Dept",
            code="OWN",
        )
        pos = PositionService.create(
            company_id=user.company_id,
            department_id=dept.id,
            title="Move Test",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        # other dept (different company)
        from apps.companies.models import Company
        other_co = Company.objects.create(
            name="Other Corp",
            industry="office",
            subscription_tier="core",
            is_active=True,
        )
        other_dept = Department.objects.create(
            company=other_co, name="Other", code="OTH"
        )
        response = hr_admin_client.patch(
            f"/api/v1/positions/{pos.id}/",
            data={"department_id": str(other_dept.id)},
            format="json",
        )
        assert response.status_code in (400, 404)


@pytest.mark.feature
class TestPositionAPIDelete:
    def test_delete_position(
        self, db, hr_admin_client: APIClient
    ):
        """DELETE /api/v1/positions/{id}/ soft-deletes and returns 204."""
        user = hr_admin_client.handler._force_user
        dept = Department.objects.create(
            company_id=user.company_id,
            name="Del Dept",
            code="DEL",
        )
        pos = PositionService.create(
            company_id=user.company_id,
            department_id=dept.id,
            title="To Delete",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        response = hr_admin_client.delete(f"/api/v1/positions/{pos.id}/")
        assert response.status_code == 204
        pos.refresh_from_db()
        assert pos.is_active is False


@pytest.mark.feature
class TestPositionAPIRestore:
    def test_restore_position(
        self, db, hr_admin_client: APIClient
    ):
        """POST /api/v1/positions/{id}/restore/ restores and returns 200."""
        user = hr_admin_client.handler._force_user
        dept = Department.objects.create(
            company_id=user.company_id,
            name="Res Dept",
            code="RES",
        )
        pos = PositionService.create(
            company_id=user.company_id,
            department_id=dept.id,
            title="To Restore",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        PositionService.soft_delete(pos.id, user.company_id)
        response = hr_admin_client.post(f"/api/v1/positions/{pos.id}/restore/")
        assert response.status_code == 200
        assert response.json()["is_active"] is True
