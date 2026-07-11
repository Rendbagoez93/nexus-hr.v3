"""
apps/departments/tests/test_department_models.py

Unit tests for Department model.
"""

from __future__ import annotations

import pytest
from django.db import IntegrityError

from apps.departments.models import Department


@pytest.mark.unit
class TestDepartmentModel:
    def test_str(self, db, company):
        """str returns 'Name (CODE)'."""
        dept = Department.objects.create(
            company=company,
            name="Engineering",
            code="ENG",
        )
        assert str(dept) == "Engineering (ENG)"

    def test_code_uniqueness_per_company(
        self, db, company
    ):
        """Same code for two departments in same company raises IntegrityError."""
        Department.objects.create(company=company, name="Dept A", code="DPT")
        with pytest.raises(IntegrityError):
            Department.objects.create(company=company, name="Dept B", code="DPT")

    def test_code_same_across_companies_allowed(
        self, db, company
    ):
        """Same code in different companies is allowed (constraint is per-company)."""
        from apps.companies.models import Company

        other_co = Company.objects.create(
            name="Other Corp",
            industry="office",
            subscription_tier="core",
            is_active=True,
        )
        Department.objects.create(company=company, name="Dept A", code="DPT")
        # Should not raise
        other = Department.objects.create(
            company=other_co, name="Other Dept", code="DPT"
        )
        assert other.pk is not None

    def test_deactivate_sets_deleted_at(
        self, db, company
    ):
        """deactivate() sets is_active=False and deleted_at to a datetime."""
        dept = Department.objects.create(
            company=company, name="To Delete", code="DEL"
        )
        assert dept.is_active is True
        assert dept.deleted_at is None
        dept.deactivate()
        assert dept.is_active is False
        assert dept.deleted_at is not None

    def test_restore_clears_deleted_at(
        self, db, company
    ):
        """restore() on inactive dept sets is_active=True and deleted_at=None."""
        dept = Department.objects.create(
            company=company, name="To Restore", code="RES"
        )
        dept.deactivate()
        assert dept.is_active is False
        dept.restore()
        assert dept.is_active is True
        assert dept.deleted_at is None
