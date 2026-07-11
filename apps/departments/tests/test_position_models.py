"""
apps/departments/tests/test_position_models.py

Unit tests for Position model.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.departments.models import Department, Position


@pytest.mark.unit
class TestPositionModel:
    def test_str(self, db, company, department):
        """str returns 'Title (level)'."""
        pos = Position.objects.create(
            company=company,
            department=department,
            title="Engineer",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        assert str(pos) == "Engineer (staff)"

    def test_salary_min_lte_max_constraint(
        self, db, company, department
    ):
        """min > max raises IntegrityError at DB level."""
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            Position.objects.create(
                company=company,
                department=department,
                title="Bad Range",
                level="staff",
                base_salary_min=Decimal("10000000"),
                base_salary_max=Decimal("5000000"),
            )

    def test_department_protect_on_delete(
        self, db, company, department
    ):
        """Deleting department with positions raises ProtectedError."""
        from django.db.models import ProtectedError

        Position.objects.create(
            company=company,
            department=department,
            title="Occupied",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        with pytest.raises(ProtectedError):
            department.delete()

    def test_deactivate(
        self, db, company, department
    ):
        """deactivate() sets is_active=False and deleted_at set."""
        pos = Position.objects.create(
            company=company,
            department=department,
            title="To Delete",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        assert pos.is_active is True
        assert pos.deleted_at is None
        pos.deactivate()
        assert pos.is_active is False
        assert pos.deleted_at is not None

    def test_restore(
        self, db, company, department
    ):
        """restore() on inactive position sets is_active=True and deleted_at=None."""
        pos = Position.objects.create(
            company=company,
            department=department,
            title="To Restore",
            level="staff",
            base_salary_min=Decimal("5000000"),
            base_salary_max=Decimal("8000000"),
        )
        pos.deactivate()
        assert pos.is_active is False
        pos.restore()
        assert pos.is_active is True
        assert pos.deleted_at is None
