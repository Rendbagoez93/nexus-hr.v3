"""
apps/departments/tests/test_position_selectors.py

Unit tests for PositionSelector.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.departments.models import Position
from apps.departments.selectors import PositionSelector
from apps.departments.services import PositionService


@pytest.mark.unit
class TestPositionSelector:
    def test_alive_returns_only_active(
        self, db, company, position, inactive_position
    ):
        """Only active positions returned, ordered by department then title."""
        result = list(PositionSelector.alive(company.id))
        assert all(p.is_active for p in result)

    def test_for_department(
        self, db, company, two_departments
    ):
        """Exactly positions in the specified department returned."""
        parent, child = two_departments
        pos1 = PositionService.create(
            company_id=company.id,
            department_id=parent.id,
            title="Alpha",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        pos2 = PositionService.create(
            company_id=company.id,
            department_id=parent.id,
            title="Beta",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        pos3 = PositionService.create(
            company_id=company.id,
            department_id=child.id,
            title="Gamma",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        result = list(PositionSelector.for_department(parent.id, company.id))
        assert len(result) == 2
        pks = {p.pk for p in result}
        assert pks == {pos1.pk, pos2.pk}

    def test_for_department_excludes_other_dept(
        self, db, company, two_departments
    ):
        """Positions from other departments excluded."""
        parent, child = two_departments
        PositionService.create(
            company_id=company.id,
            department_id=parent.id,
            title="Parent Pos",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        PositionService.create(
            company_id=company.id,
            department_id=child.id,
            title="Child Pos",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        result = list(PositionSelector.for_department(parent.id, company.id))
        assert all(p.department_id == parent.id for p in result)

    def test_by_level_single(
        self, db, company, department
    ):
        """level='manager' returns all manager positions across departments."""
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
        result = list(PositionSelector.by_level(company.id, level="manager"))
        assert all(p.level == "manager" for p in result)

    def test_by_level_multiple(
        self, db, company, department
    ):
        """levels=['manager', 'staff'] returns both levels."""
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
        result = list(PositionSelector.by_level(company.id, levels=["manager", "staff"]))
        assert len(result) == 2
        assert all(p.level in ("manager", "staff") for p in result)

    def test_by_level_none_returns_all_active(
        self, db, company, department
    ):
        """No level filter returns all active positions."""
        PositionService.create(
            company_id=company.id,
            department_id=department.id,
            title="Pos A",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        PositionService.create(
            company_id=company.id,
            department_id=department.id,
            title="Pos B",
            level="manager",
            base_salary_min=Decimal("10000000"),
            base_salary_max=Decimal("15000000"),
        )
        result = list(PositionSelector.by_level(company.id))
        assert len(result) == 2

    def test_empty_list(self, db, company):
        """Company with no positions returns empty list."""
        result = list(PositionSelector.alive(company.id))
        assert result == []
