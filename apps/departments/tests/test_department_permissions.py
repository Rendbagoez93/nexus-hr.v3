"""
apps/departments/tests/test_department_permissions.py

Permission tests for Department API — every action × every role combination.
Cross-tenant tests always assert 403 (never 404).
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.departments.models import Department
from apps.departments.services import DepartmentService


@pytest.mark.feature
class TestDepartmentPermissions:
    """Permission matrix for Department API actions."""

    @pytest.fixture
    def dept_id(self, db, company):
        dept = DepartmentService.create(
            company_id=company.id,
            name="Test Dept",
            code="TST",
        )
        return str(dept.id)

    # ---- list ----

    def test_list_hr_admin(self, db, hr_admin_client: APIClient):
        resp = hr_admin_client.get("/api/v1/departments/")
        assert resp.status_code == 200

    def test_list_manager(self, db, manager_client: APIClient):
        resp = manager_client.get("/api/v1/departments/")
        assert resp.status_code == 200

    def test_list_employee(self, db, employee_client: APIClient):
        resp = employee_client.get("/api/v1/departments/")
        assert resp.status_code == 200

    def test_list_hse_officer(self, db, hse_officer_client: APIClient):
        resp = hse_officer_client.get("/api/v1/departments/")
        assert resp.status_code == 200

    def test_list_platform_admin(self, db, platform_admin_client: APIClient):
        # Platform admin has no company, so _company_id raises PermissionDenied
        resp = platform_admin_client.get("/api/v1/departments/")
        # Expect 403 or 400 — platform admin has no company association
        assert resp.status_code in (403, 400)

    def test_list_other_company(self, db, other_company_client: APIClient):
        """other_company returns 200 (own departments, not company's)."""
        resp = other_company_client.get("/api/v1/departments/")
        assert resp.status_code == 200

    # ---- retrieve ----

    def test_retrieve_hr_admin(self, db, hr_admin_client: APIClient, dept_id: str):
        resp = hr_admin_client.get(f"/api/v1/departments/{dept_id}/")
        assert resp.status_code == 200

    def test_retrieve_manager(self, db, manager_client: APIClient, dept_id: str):
        resp = manager_client.get(f"/api/v1/departments/{dept_id}/")
        assert resp.status_code == 200

    def test_retrieve_employee(self, db, employee_client: APIClient, dept_id: str):
        resp = employee_client.get(f"/api/v1/departments/{dept_id}/")
        assert resp.status_code == 200

    def test_retrieve_hse_officer(self, db, hse_officer_client: APIClient, dept_id: str):
        resp = hse_officer_client.get(f"/api/v1/departments/{dept_id}/")
        assert resp.status_code == 200

    def test_retrieve_platform_admin(self, db, platform_admin_client: APIClient, dept_id: str):
        resp = platform_admin_client.get(f"/api/v1/departments/{dept_id}/")
        assert resp.status_code in (403, 400)

    def test_retrieve_other_company(
        self, db, other_company_client: APIClient, dept_id: str
    ):
        """Cross-tenant retrieve must return 403, never 404."""
        resp = other_company_client.get(f"/api/v1/departments/{dept_id}/")
        assert resp.status_code == 403

    # ---- create ----

    def test_create_hr_admin(self, db, hr_admin_client: APIClient):
        resp = hr_admin_client.post(
            "/api/v1/departments/",
            data={"name": "New Dept", "code": "NEW"},
            format="json",
        )
        assert resp.status_code == 201

    def test_create_manager(self, db, manager_client: APIClient):
        resp = manager_client.post(
            "/api/v1/departments/",
            data={"name": "New Dept", "code": "NEW"},
            format="json",
        )
        assert resp.status_code == 403

    def test_create_employee(self, db, employee_client: APIClient):
        resp = employee_client.post(
            "/api/v1/departments/",
            data={"name": "New Dept", "code": "NEW"},
            format="json",
        )
        assert resp.status_code == 403

    def test_create_hse_officer(self, db, hse_officer_client: APIClient):
        resp = hse_officer_client.post(
            "/api/v1/departments/",
            data={"name": "New Dept", "code": "NEW"},
            format="json",
        )
        assert resp.status_code == 403

    def test_create_platform_admin(self, db, platform_admin_client: APIClient):
        resp = platform_admin_client.post(
            "/api/v1/departments/",
            data={"name": "New Dept", "code": "NEW"},
            format="json",
        )
        assert resp.status_code in (403, 400)

    def test_create_other_company(self, db, other_company_client: APIClient):
        resp = other_company_client.post(
            "/api/v1/departments/",
            data={"name": "Other New", "code": "ONE"},
            format="json",
        )
        # 403 if they try to create in another company; if they create in
        # their own company it would be 201, but other_company_client has
        # no access to company's data — it only has access to its own.
        # Since we're not passing company's dept, they can only create
        # in their own company, which is fine — but since the client is
        # authenticated as other_company's user, this creates in other_company.
        # The 403 check only matters for cross-tenant reads/writes of
        # existing company resources, not for creating new ones.
        assert resp.status_code == 201

    # ---- patch ----

    def test_patch_hr_admin(self, db, hr_admin_client: APIClient, dept_id: str):
        resp = hr_admin_client.patch(
            f"/api/v1/departments/{dept_id}/",
            data={"name": "Updated"},
            format="json",
        )
        assert resp.status_code == 200

    def test_patch_manager(self, db, manager_client: APIClient, dept_id: str):
        resp = manager_client.patch(
            f"/api/v1/departments/{dept_id}/",
            data={"name": "Updated"},
            format="json",
        )
        assert resp.status_code == 403

    def test_patch_employee(self, db, employee_client: APIClient, dept_id: str):
        resp = employee_client.patch(
            f"/api/v1/departments/{dept_id}/",
            data={"name": "Updated"},
            format="json",
        )
        assert resp.status_code == 403

    def test_patch_hse_officer(self, db, hse_officer_client: APIClient, dept_id: str):
        resp = hse_officer_client.patch(
            f"/api/v1/departments/{dept_id}/",
            data={"name": "Updated"},
            format="json",
        )
        assert resp.status_code == 403

    def test_patch_platform_admin(self, db, platform_admin_client: APIClient, dept_id: str):
        resp = platform_admin_client.patch(
            f"/api/v1/departments/{dept_id}/",
            data={"name": "Updated"},
            format="json",
        )
        assert resp.status_code in (403, 400)

    def test_patch_other_company(self, db, other_company_client: APIClient, dept_id: str):
        """Cross-tenant patch must return 403."""
        resp = other_company_client.patch(
            f"/api/v1/departments/{dept_id}/",
            data={"name": "Hijacked"},
            format="json",
        )
        assert resp.status_code == 403

    # ---- delete ----

    def test_delete_hr_admin(self, db, hr_admin_client: APIClient, dept_id: str):
        resp = hr_admin_client.delete(f"/api/v1/departments/{dept_id}/")
        assert resp.status_code == 204

    def test_delete_manager(self, db, manager_client: APIClient, dept_id: str):
        resp = manager_client.delete(f"/api/v1/departments/{dept_id}/")
        assert resp.status_code == 403

    def test_delete_employee(self, db, employee_client: APIClient, dept_id: str):
        resp = employee_client.delete(f"/api/v1/departments/{dept_id}/")
        assert resp.status_code == 403

    def test_delete_hse_officer(self, db, hse_officer_client: APIClient, dept_id: str):
        resp = hse_officer_client.delete(f"/api/v1/departments/{dept_id}/")
        assert resp.status_code == 403

    def test_delete_platform_admin(self, db, platform_admin_client: APIClient, dept_id: str):
        resp = platform_admin_client.delete(f"/api/v1/departments/{dept_id}/")
        assert resp.status_code in (403, 400)

    def test_delete_other_company(self, db, other_company_client: APIClient, dept_id: str):
        """Cross-tenant delete must return 403."""
        resp = other_company_client.delete(f"/api/v1/departments/{dept_id}/")
        assert resp.status_code == 403

    # ---- restore ----

    def test_restore_hr_admin(self, db, hr_admin_client: APIClient, company):
        dept = DepartmentService.create(
            company_id=company.id,
            name="Deleted",
            code="DEL",
        )
        DepartmentService.soft_delete(dept.id, company.id)
        resp = hr_admin_client.post(f"/api/v1/departments/{dept.id}/restore/")
        assert resp.status_code == 200

    def test_restore_manager(self, db, manager_client: APIClient, company):
        dept = DepartmentService.create(
            company_id=company.id,
            name="Deleted",
            code="DEL",
        )
        DepartmentService.soft_delete(dept.id, company.id)
        resp = manager_client.post(f"/api/v1/departments/{dept.id}/restore/")
        assert resp.status_code == 403

    def test_restore_employee(self, db, employee_client: APIClient, company):
        dept = DepartmentService.create(
            company_id=company.id,
            name="Deleted",
            code="DEL",
        )
        DepartmentService.soft_delete(dept.id, company.id)
        resp = employee_client.post(f"/api/v1/departments/{dept.id}/restore/")
        assert resp.status_code == 403

    def test_restore_hse_officer(self, db, hse_officer_client: APIClient, company):
        dept = DepartmentService.create(
            company_id=company.id,
            name="Deleted",
            code="DEL",
        )
        DepartmentService.soft_delete(dept.id, company.id)
        resp = hse_officer_client.post(f"/api/v1/departments/{dept.id}/restore/")
        assert resp.status_code == 403

    def test_restore_platform_admin(self, db, platform_admin_client: APIClient, company):
        dept = DepartmentService.create(
            company_id=company.id,
            name="Deleted",
            code="DEL",
        )
        DepartmentService.soft_delete(dept.id, company.id)
        resp = platform_admin_client.post(f"/api/v1/departments/{dept.id}/restore/")
        assert resp.status_code in (403, 400)

    def test_restore_other_company(self, db, other_company_client: APIClient, company):
        dept = DepartmentService.create(
            company_id=company.id,
            name="Deleted",
            code="DEL",
        )
        DepartmentService.soft_delete(dept.id, company.id)
        resp = other_company_client.post(f"/api/v1/departments/{dept.id}/restore/")
        assert resp.status_code == 403

    # ---- tree ----

    def test_tree_hr_admin(self, db, hr_admin_client: APIClient):
        resp = hr_admin_client.get("/api/v1/departments/tree/")
        assert resp.status_code == 200

    def test_tree_manager(self, db, manager_client: APIClient):
        resp = manager_client.get("/api/v1/departments/tree/")
        assert resp.status_code == 200

    def test_tree_employee(self, db, employee_client: APIClient):
        resp = employee_client.get("/api/v1/departments/tree/")
        assert resp.status_code == 200

    def test_tree_hse_officer(self, db, hse_officer_client: APIClient):
        resp = hse_officer_client.get("/api/v1/departments/tree/")
        assert resp.status_code == 200

    def test_tree_platform_admin(self, db, platform_admin_client: APIClient):
        resp = platform_admin_client.get("/api/v1/departments/tree/")
        assert resp.status_code in (403, 400)

    def test_tree_other_company(self, db, other_company_client: APIClient):
        resp = other_company_client.get("/api/v1/departments/tree/")
        # other_company_client has its own company, so it should return 200
        # with that company's tree (not the original company's)
        assert resp.status_code == 200
