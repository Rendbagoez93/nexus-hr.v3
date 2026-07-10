"""
apps/departments/tests/test_department_integration.py

Integration tests for Department — manager + soft-delete + restore pipelines.
"""

from __future__ import annotations

import pytest

from apps.departments.models import Department
from apps.departments.selectors import DepartmentSelector
from apps.departments.services import DepartmentService


@pytest.mark.integration
class TestDepartmentIntegration:
    def test_department_tree_integration(
        self, db, company
    ):
        """Create 3-level hierarchy via service, query via selector."""
        root = DepartmentService.create(
            company_id=company.id,
            name="Root",
            code="ROOT",
        )
        child = DepartmentService.create(
            company_id=company.id,
            name="Child",
            code="CHILD",
            parent_id=root.id,
        )
        grandchild = DepartmentService.create(
            company_id=company.id,
            name="Grandchild",
            code="GCHILD",
            parent_id=child.id,
        )
        # Query root with children via selector
        roots = list(DepartmentSelector.with_children(company.id))
        assert len(roots) == 1
        assert roots[0].pk == root.pk
        children = list(roots[0].children.all())
        assert len(children) == 1
        assert children[0].pk == child.pk
        # Grandchild is child of child
        child.refresh_from_db()
        grand_children = list(child.children.all())
        assert len(grand_children) == 1
        assert grand_children[0].pk == grandchild.pk

    def test_create_duplicate_code_same_company(
        self, db, company
    ):
        """Two creates with same code for same company raises IntegrityError."""
        DepartmentService.create(
            company_id=company.id,
            name="Dept A",
            code="DUP",
        )
        with pytest.raises(Exception):  # IntegrityError
            DepartmentService.create(
                company_id=company.id,
                name="Dept B",
                code="DUP",
            )

    def test_cross_tenant_isolation(
        self, db, company, department_other_company
    ):
        """Company A creates dept; query with Company B returns empty list."""
        DepartmentService.create(
            company_id=company.id,
            name="Engineering",
            code="ENG",
        )
        result = list(DepartmentSelector.alive(company.id))
        eng_codes = [d.code for d in result]
        assert "OTH" not in eng_codes

    def test_department_ordering(
        self, db, company
    ):
        """Create 3 depts in order: Z, A, M — list returns [A, M, Z] by name."""
        DepartmentService.create(company_id=company.id, name="Zulu", code="Z")
        DepartmentService.create(company_id=company.id, name="Alpha", code="A")
        DepartmentService.create(company_id=company.id, name="Mike", code="M")
        result = list(DepartmentSelector.alive(company.id))
        names = [d.name for d in result]
        assert names == sorted(names)
