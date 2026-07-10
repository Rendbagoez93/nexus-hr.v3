"""
apps/departments/tests/test_department_selectors.py

Unit tests for DepartmentSelector.
"""

from __future__ import annotations

import pytest

from apps.departments.models import Department
from apps.departments.selectors import DepartmentSelector


@pytest.mark.unit
class TestDepartmentSelector:
    def test_alive_returns_only_active(
        self, db, company, department, inactive_department
    ):
        """Only is_active=True returned, ordered by name."""
        result = list(DepartmentSelector.alive(company.id))
        codes = [d.code for d in result]
        assert "DEP" not in codes
        assert "ENG" in codes
        # Check ordering
        if len(result) > 1:
            names = [d.name for d in result]
            assert names == sorted(names)

    def test_root_departments(
        self, db, company, two_departments
    ):
        """Only root (no parent) departments returned."""
        parent, child = two_departments
        result = list(DepartmentSelector.root_departments(company.id))
        assert len(result) == 1
        assert result[0].pk == parent.pk

    def test_children_of(
        self, db, company, two_departments
    ):
        """Exactly direct children returned, ordered by name."""
        parent, child = two_departments
        result = list(DepartmentSelector.children_of(parent.id, company.id))
        assert len(result) == 1
        assert result[0].pk == child.pk

    def test_with_children(
        self, db, company, two_departments
    ):
        """Root returned with children prefetched."""
        parent, child = two_departments
        result = list(DepartmentSelector.with_children(company.id))
        assert len(result) == 1
        assert result[0].pk == parent.pk
        # Prefetched children should be accessible without N+1
        children = list(result[0].children.all())
        assert len(children) == 1
        assert children[0].pk == child.pk
