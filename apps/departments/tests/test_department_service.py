"""
apps/departments/tests/test_department_service.py

Unit tests for DepartmentService.
All tests are marked @pytest.mark.unit — no HTTP, no browser, DB allowed.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from apps.departments.exceptions import DepartmentError
from apps.departments.models import Department
from apps.departments.services import DepartmentService


@pytest.mark.unit
class TestDepartmentServiceCreate:
    def test_create_department(
        self, db, company
    ):
        """Department created with correct fields and is_active=True."""
        dept = DepartmentService.create(
            company_id=company.id,
            name="Engineering",
            code="ENG",
        )
        assert dept.company_id == company.id
        assert dept.name == "Engineering"
        assert dept.code == "ENG"
        assert dept.is_active is True
        assert dept.parent is None

    def test_create_department_with_parent(
        self, db, company, two_departments
    ):
        """Department created with parent FK set correctly."""
        parent, _ = two_departments
        child = DepartmentService.create(
            company_id=company.id,
            name="Backend",
            code="BE",
            parent_id=parent.id,
        )
        assert child.parent_id == parent.id

    def test_create_department_parent_not_found(self, db, company):
        """Non-existent parent_id raises DepartmentError 404."""
        with pytest.raises(DepartmentError) as exc_info:
            DepartmentService.create(
                company_id=company.id,
                name="Orphan",
                code="ORP",
                parent_id=uuid4(),
            )
        assert exc_info.value.status_code == 404
        assert "Parent department not found" in str(exc_info.value.detail)

    def test_create_department_parent_wrong_company(
        self, db, company, department_other_company
    ):
        """Parent department from another company raises DepartmentError 404."""
        with pytest.raises(DepartmentError) as exc_info:
            DepartmentService.create(
                company_id=company.id,
                name="Orphan",
                code="ORP",
                parent_id=department_other_company.id,
            )
        assert exc_info.value.status_code == 404
        assert "Parent department not found" in str(exc_info.value.detail)


@pytest.mark.unit
class TestDepartmentServiceGet:
    def test_get_by_id(
        self, db, company, department
    ):
        """Valid pk + company_id returns the Department instance."""
        found = DepartmentService.get_by_id(department.id, company.id)
        assert found.pk == department.pk

    def test_get_by_id_not_found(self, db, company):
        """Non-existent pk raises DepartmentError 404."""
        with pytest.raises(DepartmentError) as exc_info:
            DepartmentService.get_by_id(uuid4(), company.id)
        assert exc_info.value.status_code == 404
        assert "Department not found" in str(exc_info.value.detail)


@pytest.mark.unit
class TestDepartmentServiceUpdate:
    def test_update_name(
        self, db, company, department
    ):
        """Field updated and saved."""
        updated = DepartmentService.update(
            department.id,
            company.id,
            name="Engineering Ops",
        )
        assert updated.name == "Engineering Ops"

    def test_update_code_normalizes_to_uppercase(
        self, db, company, department
    ):
        """Mixed-case code saved as uppercase."""
        updated = DepartmentService.update(
            department.id,
            company.id,
            code="en-g",
        )
        assert updated.code == "EN-G"

    def test_update_parent_to_null(
        self, db, company, two_departments
    ):
        """Department with existing parent can be updated with parent_id=None."""
        parent, child = two_departments
        assert child.parent_id is not None
        updated = DepartmentService.update(
            child.id,
            company.id,
            parent_id=None,
        )
        assert updated.parent_id is None


@pytest.mark.unit
class TestDepartmentServiceSoftDelete:
    def test_soft_delete(
        self, db, company, department
    ):
        """is_active=False and deleted_at set."""
        assert department.is_active is True
        DepartmentService.soft_delete(department.id, company.id)
        department.refresh_from_db()
        assert department.is_active is False
        assert department.deleted_at is not None

    def test_restore(
        self, db, company, inactive_department
    ):
        """Soft-deleted dept restored with is_active=True and deleted_at=None."""
        assert inactive_department.is_active is False
        restored = DepartmentService.restore(inactive_department.id, company.id)
        assert restored.is_active is True
        assert restored.deleted_at is None

    def test_restore_not_found_inactive(self, db, company):
        """Non-existent pk raises DepartmentError 404."""
        with pytest.raises(DepartmentError) as exc_info:
            DepartmentService.restore(uuid4(), company.id)
        assert exc_info.value.status_code == 404

    def test_restore_not_found_active(self, db, company, department):
        """Already-active dept raises DepartmentError 404."""
        with pytest.raises(DepartmentError) as exc_info:
            DepartmentService.restore(department.id, company.id)
        assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestDepartmentServiceList:
    def test_list_all_active(
        self, db, company, department, inactive_department
    ):
        """Only is_active=True departments returned."""
        result = DepartmentService.list_for_company(company.id, is_active=True)
        assert all(d.is_active for d in result)
        assert len(result) >= 1

    def test_list_include_inactive(
        self, db, company, department, inactive_department
    ):
        """Both active and inactive returned when is_active=False."""
        result = DepartmentService.list_for_company(company.id, is_active=False)
        assert len(result) == 2

    def test_list_filter_by_parent(
        self, db, company, two_departments
    ):
        """Only direct children of root department returned."""
        parent, child = two_departments
        result = DepartmentService.list_for_company(
            company.id, parent_id=parent.id, is_active=True
        )
        assert len(result) == 1
        assert result[0].pk == child.pk

    def test_list_empty(self, db, company):
        """Company with no departments returns empty list."""
        result = DepartmentService.list_for_company(company.id)
        assert result == []
