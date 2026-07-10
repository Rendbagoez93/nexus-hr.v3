"""
apps/departments/tests/test_position_service.py

Unit tests for PositionService.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from apps.departments.exceptions import PositionError
from apps.departments.models import Position
from apps.departments.services import PositionService


@pytest.mark.unit
class TestPositionServiceCreate:
    def test_create_position(
        self, db, company, department
    ):
        """Position created with correct fields."""
        pos = PositionService.create(
            company_id=company.id,
            department_id=department.id,
            title="Engineer",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        assert pos.title == "Engineer"
        assert pos.level == "staff"
        assert pos.base_salary_min == Decimal("5000000")
        assert pos.base_salary_max == Decimal("8000000")
        assert pos.is_active is True
        assert pos.department_id == department.id

    def test_create_min_less_than_max(
        self, db, company, department
    ):
        """min=5_000_000, max=8_000_000 — position created successfully."""
        pos = PositionService.create(
            company_id=company.id,
            department_id=department.id,
            title="Mid Engineer",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        assert pos.pk is not None

    def test_create_min_equals_max(
        self, db, company, department
    ):
        """min=5_000_000, max=5_000_000 — equal is allowed."""
        pos = PositionService.create(
            company_id=company.id,
            department_id=department.id,
            title="Fixed Salary Role",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("5000000"),
        )
        assert pos.pk is not None

    def test_create_min_greater_than_max(
        self, db, company, department
    ):
        """min=10_000_000 > max=5_000_000 raises PositionError 400."""
        with pytest.raises(PositionError) as exc_info:
            PositionService.create(
                company_id=company.id,
                department_id=department.id,
                title="Bad Range",
                level="staff",
                base_salary_min=Decimal("10000000"),
                base_salary_max=Decimal("5000000"),
            )
        assert exc_info.value.status_code == 400
        assert "salary" in str(exc_info.value.detail).lower()

    def test_create_department_not_found(self, db, company):
        """Non-existent department_id raises PositionError 404."""
        with pytest.raises(PositionError) as exc_info:
            PositionService.create(
                company_id=company.id,
                department_id=uuid4(),
                title="Orphan",
                level="staff",
                base_salary_min=Decimal("5000000"),
                base_salary_max=Decimal("8000000"),
            )
        assert exc_info.value.status_code == 404
        assert "Department not found" in str(exc_info.value.detail)

    def test_create_department_wrong_company(
        self, db, company, department_other_company
    ):
        """department_id from another company raises PositionError 404."""
        with pytest.raises(PositionError) as exc_info:
            PositionService.create(
                company_id=company.id,
                department_id=department_other_company.id,
                title="Orphan",
                level="staff",
                base_salary_min=Decimal("5000000"),
                base_salary_max=Decimal("8000000"),
            )
        assert exc_info.value.status_code == 404
        assert "Department not found" in str(exc_info.value.detail)


@pytest.mark.unit
class TestPositionServiceGet:
    def test_get_by_id(
        self, db, company, position
    ):
        """Valid pk + company_id returns Position instance."""
        found = PositionService.get_by_id(position.id, company.id)
        assert found.pk == position.pk

    def test_get_by_id_not_found(self, db, company):
        """Non-existent pk raises PositionError 404."""
        with pytest.raises(PositionError) as exc_info:
            PositionService.get_by_id(uuid4(), company.id)
        assert exc_info.value.status_code == 404
        assert "Position not found" in str(exc_info.value.detail)


@pytest.mark.unit
class TestPositionServiceUpdate:
    def test_update_salary_range(
        self, db, company, position
    ):
        """base_salary_min=6_000_000 and base_salary_max=9_000_000 both updated."""
        updated = PositionService.update(
            position.id,
            company.id,
            base_salary_min=Decimal("6000000"),
            base_salary_max=Decimal("9000000"),
        )
        assert updated.base_salary_min == Decimal("6000000")
        assert updated.base_salary_max == Decimal("9000000")

    def test_update_min_breaches_max(
        self, db, company, position
    ):
        """new base_salary_min > existing base_salary_max raises PositionError 400."""
        with pytest.raises(PositionError) as exc_info:
            PositionService.update(
                position.id,
                company.id,
                base_salary_min=Decimal("15000000"),
            )
        assert exc_info.value.status_code == 400
        assert "salary" in str(exc_info.value.detail).lower()

    def test_update_max_breaches_min(
        self, db, company, position
    ):
        """new base_salary_max < existing base_salary_min raises PositionError 400."""
        with pytest.raises(PositionError) as exc_info:
            PositionService.update(
                position.id,
                company.id,
                base_salary_max=Decimal("1000000"),
            )
        assert exc_info.value.status_code == 400
        assert "salary" in str(exc_info.value.detail).lower()

    def test_update_department(
        self, db, company, two_departments
    ):
        """department_id updated to a different dept."""
        parent, new_dept = two_departments
        pos = PositionService.create(
            company_id=company.id,
            department_id=parent.id,
            title="Mover",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        updated = PositionService.update(
            pos.id,
            company.id,
            department_id=new_dept.id,
        )
        assert updated.department_id == new_dept.id

    def test_update_department_not_found(
        self, db, company, position
    ):
        """Non-existent department_id raises PositionError 404."""
        with pytest.raises(PositionError) as exc_info:
            PositionService.update(
                position.id,
                company.id,
                department_id=uuid4(),
            )
        assert exc_info.value.status_code == 404

    def test_update_department_wrong_company(
        self, db, company, position, department_other_company
    ):
        """department_id from another company raises PositionError 404."""
        with pytest.raises(PositionError) as exc_info:
            PositionService.update(
                position.id,
                company.id,
                department_id=department_other_company.id,
            )
        assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestPositionServiceSoftDelete:
    def test_soft_delete(
        self, db, company, position
    ):
        """is_active=False and deleted_at set."""
        assert position.is_active is True
        PositionService.soft_delete(position.id, company.id)
        position.refresh_from_db()
        assert position.is_active is False
        assert position.deleted_at is not None

    def test_restore(
        self, db, company, inactive_position
    ):
        """Soft-deleted position restored with is_active=True and deleted_at=None."""
        assert inactive_position.is_active is False
        restored = PositionService.restore(inactive_position.id, company.id)
        assert restored.is_active is True
        assert restored.deleted_at is None

    def test_restore_not_found_inactive(self, db, company):
        """Non-existent pk raises PositionError 404."""
        with pytest.raises(PositionError) as exc_info:
            PositionService.restore(uuid4(), company.id)
        assert exc_info.value.status_code == 404

    def test_restore_not_found_active(self, db, company, position):
        """Already-active position raises PositionError 404."""
        with pytest.raises(PositionError) as exc_info:
            PositionService.restore(position.id, company.id)
        assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestPositionServiceList:
    def test_list_all_active(
        self, db, company, position, inactive_position
    ):
        """Only active positions returned."""
        result = PositionService.list_for_company(company.id, is_active=True)
        assert all(p.is_active for p in result)

    def test_list_by_department(
        self, db, company, two_departments, position
    ):
        """department_id filter returns only positions in that dept."""
        parent, child = two_departments
        # position is in parent dept
        result = PositionService.list_for_company(
            company.id, department_id=parent.id, is_active=True
        )
        assert all(p.department_id == parent.id for p in result)

    def test_list_by_level(
        self, db, company, department
    ):
        """level='manager' filter returns only manager-level positions."""
        PositionService.create(
            company_id=company.id,
            department_id=department.id,
            title="Manager A",
            level="manager",
            base_salary_min=Decimal("10000000"),
            base_salary_max=Decimal("15000000"),
        )
        PositionService.create(
            company_id=company.id,
            department_id=department.id,
            title="Staff A",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        result = PositionService.list_for_company(
            company.id, level="manager", is_active=True
        )
        assert all(p.level == "manager" for p in result)

    def test_list_by_department_and_level(
        self, db, company, two_departments
    ):
        """Both department_id and level filters combined."""
        parent, child = two_departments
        pos1 = PositionService.create(
            company_id=company.id,
            department_id=parent.id,
            title="Mgr Parent",
            level="manager",
            base_salary_min=Decimal("10000000"),
            base_salary_max=Decimal("15000000"),
        )
        pos2 = PositionService.create(
            company_id=company.id,
            department_id=child.id,
            title="Staff Child",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        result = PositionService.list_for_company(
            company.id,
            department_id=parent.id,
            level="manager",
            is_active=True,
        )
        assert len(result) == 1
        assert result[0].pk == pos1.pk
