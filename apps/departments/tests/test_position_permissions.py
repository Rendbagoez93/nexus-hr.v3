"""
apps/departments/tests/test_position_permissions.py

Permission tests for Position API — every action × every role combination.
Cross-tenant tests always assert 403 (never 404).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.departments.models import Department
from apps.departments.services import PositionService


@pytest.mark.feature
class TestPositionPermissions:
    """Permission matrix for Position API actions."""

    @pytest.fixture
    def pos_id(self, db, company):
        dept = Department.objects.create(
            company_id=company.id,
            name="Perm Dept",
            code="PRM",
        )
        pos = PositionService.create(
            company_id=company.id,
            department_id=dept.id,
            title="Perm Pos",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        return str(pos.id)

    # ---- list ----

    def test_list_hr_admin(self, db, hr_admin_client: APIClient):
        resp = hr_admin_client.get("/api/v1/positions/")
        assert resp.status_code == 200

    def test_list_manager(self, db, manager_client: APIClient):
        resp = manager_client.get("/api/v1/positions/")
        assert resp.status_code == 200

    def test_list_employee(self, db, employee_client: APIClient):
        resp = employee_client.get("/api/v1/positions/")
        assert resp.status_code == 200

    def test_list_hse_officer(self, db, hse_officer_client: APIClient):
        resp = hse_officer_client.get("/api/v1/positions/")
        assert resp.status_code == 200

    def test_list_platform_admin(self, db, platform_admin_client: APIClient):
        resp = platform_admin_client.get("/api/v1/positions/")
        assert resp.status_code in (403, 400)

    def test_list_other_company(self, db, other_company_client: APIClient):
        resp = other_company_client.get("/api/v1/positions/")
        assert resp.status_code == 200

    # ---- retrieve ----

    def test_retrieve_hr_admin(self, db, hr_admin_client: APIClient, pos_id: str):
        resp = hr_admin_client.get(f"/api/v1/positions/{pos_id}/")
        assert resp.status_code == 200

    def test_retrieve_manager(self, db, manager_client: APIClient, pos_id: str):
        resp = manager_client.get(f"/api/v1/positions/{pos_id}/")
        assert resp.status_code == 200

    def test_retrieve_employee(self, db, employee_client: APIClient, pos_id: str):
        resp = employee_client.get(f"/api/v1/positions/{pos_id}/")
        assert resp.status_code == 200

    def test_retrieve_hse_officer(self, db, hse_officer_client: APIClient, pos_id: str):
        resp = hse_officer_client.get(f"/api/v1/positions/{pos_id}/")
        assert resp.status_code == 200

    def test_retrieve_platform_admin(self, db, platform_admin_client: APIClient, pos_id: str):
        resp = platform_admin_client.get(f"/api/v1/positions/{pos_id}/")
        assert resp.status_code in (403, 400)

    def test_retrieve_other_company(self, db, other_company_client: APIClient, pos_id: str):
        """Cross-tenant retrieve must return 403."""
        resp = other_company_client.get(f"/api/v1/positions/{pos_id}/")
        assert resp.status_code == 403

    # ---- create ----

    def test_create_hr_admin(self, db, hr_admin_client: APIClient):
        user = hr_admin_client.handler._force_user
        dept = Department.objects.create(
            company_id=user.company_id,
            name="Create Perm Dept",
            code="CPD",
        )
        resp = hr_admin_client.post(
            "/api/v1/positions/",
            data={
                "department_id": str(dept.id),
                "title": "New Position",
                "level": "staff",
                "base_salary_min": "5000000",
                "base_salary_max": "8000000",
            },
            format="json",
        )
        assert resp.status_code == 201

    def test_create_manager(self, db, manager_client: APIClient):
        resp = manager_client.post(
            "/api/v1/positions/",
            data={
                "department_id": "00000000-0000-0000-0000-000000000001",
                "title": "Manager Created",
                "level": "staff",
                "base_salary_min": "5000000",
                "base_salary_max": "8000000",
            },
            format="json",
        )
        assert resp.status_code == 403

    def test_create_employee(self, db, employee_client: APIClient):
        resp = employee_client.post(
            "/api/v1/positions/",
            data={
                "department_id": "00000000-0000-0000-0000-000000000001",
                "title": "Employee Created",
                "level": "staff",
                "base_salary_min": "5000000",
                "base_salary_max": "8000000",
            },
            format="json",
        )
        assert resp.status_code == 403

    def test_create_hse_officer(self, db, hse_officer_client: APIClient):
        resp = hse_officer_client.post(
            "/api/v1/positions/",
            data={
                "department_id": "00000000-0000-0000-0000-000000000001",
                "title": "HSE Created",
                "level": "staff",
                "base_salary_min": "5000000",
                "base_salary_max": "8000000",
            },
            format="json",
        )
        assert resp.status_code == 403

    def test_create_platform_admin(self, db, platform_admin_client: APIClient):
        resp = platform_admin_client.post(
            "/api/v1/positions/",
            data={
                "department_id": "00000000-0000-0000-0000-000000000001",
                "title": "Platform Created",
                "level": "staff",
                "base_salary_min": "5000000",
                "base_salary_max": "8000000",
            },
            format="json",
        )
        assert resp.status_code in (403, 400)

    def test_create_other_company(self, db, other_company_client: APIClient):
        """other_company_client creates in their own company — 201."""
        user = other_company_client.handler._force_user
        dept = Department.objects.create(
            company_id=user.company_id,
            name="Other Create Dept",
            code="OCD",
        )
        resp = other_company_client.post(
            "/api/v1/positions/",
            data={
                "department_id": str(dept.id),
                "title": "Other Company Pos",
                "level": "staff",
                "base_salary_min": "5000000",
                "base_salary_max": "8000000",
            },
            format="json",
        )
        assert resp.status_code == 201

    # ---- patch ----

    def test_patch_hr_admin(self, db, hr_admin_client: APIClient, pos_id: str):
        resp = hr_admin_client.patch(
            f"/api/v1/positions/{pos_id}/",
            data={"title": "Updated Title"},
            format="json",
        )
        assert resp.status_code == 200

    def test_patch_manager(self, db, manager_client: APIClient, pos_id: str):
        resp = manager_client.patch(
            f"/api/v1/positions/{pos_id}/",
            data={"title": "Manager Updated"},
            format="json",
        )
        assert resp.status_code == 403

    def test_patch_employee(self, db, employee_client: APIClient, pos_id: str):
        resp = employee_client.patch(
            f"/api/v1/positions/{pos_id}/",
            data={"title": "Employee Updated"},
            format="json",
        )
        assert resp.status_code == 403

    def test_patch_hse_officer(self, db, hse_officer_client: APIClient, pos_id: str):
        resp = hse_officer_client.patch(
            f"/api/v1/positions/{pos_id}/",
            data={"title": "HSE Updated"},
            format="json",
        )
        assert resp.status_code == 403

    def test_patch_platform_admin(self, db, platform_admin_client: APIClient, pos_id: str):
        resp = platform_admin_client.patch(
            f"/api/v1/positions/{pos_id}/",
            data={"title": "Platform Updated"},
            format="json",
        )
        assert resp.status_code in (403, 400)

    def test_patch_other_company(self, db, other_company_client: APIClient, pos_id: str):
        """Cross-tenant patch must return 403."""
        resp = other_company_client.patch(
            f"/api/v1/positions/{pos_id}/",
            data={"title": "Hijacked"},
            format="json",
        )
        assert resp.status_code == 403

    # ---- delete ----

    def test_delete_hr_admin(self, db, hr_admin_client: APIClient, pos_id: str):
        resp = hr_admin_client.delete(f"/api/v1/positions/{pos_id}/")
        assert resp.status_code == 204

    def test_delete_manager(self, db, manager_client: APIClient, pos_id: str):
        resp = manager_client.delete(f"/api/v1/positions/{pos_id}/")
        assert resp.status_code == 403

    def test_delete_employee(self, db, employee_client: APIClient, pos_id: str):
        resp = employee_client.delete(f"/api/v1/positions/{pos_id}/")
        assert resp.status_code == 403

    def test_delete_hse_officer(self, db, hse_officer_client: APIClient, pos_id: str):
        resp = hse_officer_client.delete(f"/api/v1/positions/{pos_id}/")
        assert resp.status_code == 403

    def test_delete_platform_admin(self, db, platform_admin_client: APIClient, pos_id: str):
        resp = platform_admin_client.delete(f"/api/v1/positions/{pos_id}/")
        assert resp.status_code in (403, 400)

    def test_delete_other_company(self, db, other_company_client: APIClient, pos_id: str):
        """Cross-tenant delete must return 403."""
        resp = other_company_client.delete(f"/api/v1/positions/{pos_id}/")
        assert resp.status_code == 403

    # ---- restore ----

    def test_restore_hr_admin(self, db, hr_admin_client: APIClient, company):
        dept = Department.objects.create(
            company_id=company.id,
            name="Restore Dept",
            code="RRD",
        )
        pos = PositionService.create(
            company_id=company.id,
            department_id=dept.id,
            title="To Restore",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        PositionService.soft_delete(pos.id, company.id)
        resp = hr_admin_client.post(f"/api/v1/positions/{pos.id}/restore/")
        assert resp.status_code == 200

    def test_restore_manager(self, db, manager_client: APIClient, company):
        dept = Department.objects.create(
            company_id=company.id,
            name="ResMgr Dept",
            code="RMD",
        )
        pos = PositionService.create(
            company_id=company.id,
            department_id=dept.id,
            title="Mgr Restore",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        PositionService.soft_delete(pos.id, company.id)
        resp = manager_client.post(f"/api/v1/positions/{pos.id}/restore/")
        assert resp.status_code == 403

    def test_restore_employee(self, db, employee_client: APIClient, company):
        dept = Department.objects.create(
            company_id=company.id,
            name="ResEmp Dept",
            code="RED",
        )
        pos = PositionService.create(
            company_id=company.id,
            department_id=dept.id,
            title="Emp Restore",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        PositionService.soft_delete(pos.id, company.id)
        resp = employee_client.post(f"/api/v1/positions/{pos.id}/restore/")
        assert resp.status_code == 403

    def test_restore_hse_officer(self, db, hse_officer_client: APIClient, company):
        dept = Department.objects.create(
            company_id=company.id,
            name="ResHSE Dept",
            code="RHS",
        )
        pos = PositionService.create(
            company_id=company.id,
            department_id=dept.id,
            title="HSE Restore",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        PositionService.soft_delete(pos.id, company.id)
        resp = hse_officer_client.post(f"/api/v1/positions/{pos.id}/restore/")
        assert resp.status_code == 403

    def test_restore_platform_admin(self, db, platform_admin_client: APIClient, company):
        dept = Department.objects.create(
            company_id=company.id,
            name="ResPlat Dept",
            code="RPD",
        )
        pos = PositionService.create(
            company_id=company.id,
            department_id=dept.id,
            title="Plat Restore",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        PositionService.soft_delete(pos.id, company.id)
        resp = platform_admin_client.post(f"/api/v1/positions/{pos.id}/restore/")
        assert resp.status_code in (403, 400)

    def test_restore_other_company(self, db, other_company_client: APIClient, company):
        dept = Department.objects.create(
            company_id=company.id,
            name="Res Oth Dept",
            code="ROD",
        )
        pos = PositionService.create(
            company_id=company.id,
            department_id=dept.id,
            title="Oth Restore",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        PositionService.soft_delete(pos.id, company.id)
        resp = other_company_client.post(f"/api/v1/positions/{pos.id}/restore/")
        assert resp.status_code == 403
