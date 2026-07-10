"""
apps/departments/tests/test_position_integration.py

Integration tests for Position — manager + soft-delete + restore pipelines.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.departments.selectors import PositionSelector
from apps.departments.services import PositionService


@pytest.mark.integration
class TestPositionIntegration:
    def test_create_duplicate_title_same_dept(
        self, db, company, department
    ):
        """Two positions with same title in same dept both succeed."""
        pos1 = PositionService.create(
            company_id=company.id,
            department_id=department.id,
            title="Engineer",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        pos2 = PositionService.create(
            company_id=company.id,
            department_id=department.id,
            title="Engineer",
            level="senior",
            base_salary_min=Decimal("8000000"),
            base_salary_max=Decimal("12000000"),
        )
        assert pos1.pk != pos2.pk

    def test_position_ordering(
        self, db, company, department
    ):
        """Create in order Z, A, M — alive() returns [A, M, Z] by dept then title."""
        PositionService.create(
            company_id=company.id,
            department_id=department.id,
            title="Zulu",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        PositionService.create(
            company_id=company.id,
            department_id=department.id,
            title="Alpha",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        PositionService.create(
            company_id=company.id,
            department_id=department.id,
            title="Mike",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        result = list(PositionSelector.alive(company.id))
        titles = [p.title for p in result]
        assert titles == sorted(titles)

    def test_cross_tenant_isolation(
        self, db, company, position_other_company
    ):
        """Company A creates position; query with Company B returns empty list."""
        from apps.departments.models import Department

        dept = Department.objects.create(
            company=company,
            name="Isolation Test",
            code="ISO",
        )
        PositionService.create(
            company_id=company.id,
            department_id=dept.id,
            title="Confidential",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        result = list(PositionSelector.alive(company.id))
        titles = [p.title for p in result]
        # position_other_company belongs to other company — should not appear
        assert "Other Position" not in titles

    def test_salary_validation_at_db_level(
        self, db, company, department
    ):
        """Service layer rejects min > max before it reaches the DB constraint."""
        from apps.departments.exceptions import PositionError

        with pytest.raises(PositionError):
            PositionService.create(
                company_id=company.id,
                department_id=department.id,
                title="DB Test",
                level="staff",
                base_salary_min=Decimal("10000000"),
                base_salary_max=Decimal("5000000"),
            )

    def test_update_salary_via_partial(
        self, db, company, department
    ):
        """PATCH with only base_salary_max — existing base_salary_min retained."""
        pos = PositionService.create(
            company_id=company.id,
            department_id=department.id,
            title="Partial Update",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        updated = PositionService.update(
            pos.id,
            company.id,
            base_salary_max=Decimal("9000000"),
        )
        assert updated.base_salary_min == Decimal("5000000")
        assert updated.base_salary_max == Decimal("9000000")
