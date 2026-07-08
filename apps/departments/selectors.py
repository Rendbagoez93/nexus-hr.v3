"""
apps/departments/selectors.py

Query helpers for Department and Position.
These complement SoftDeleteMixin.alive() with company-scoped, filterable queries.
"""

from django.db.models import QuerySet

from apps.departments.models import Department, Position


class DepartmentSelector:
    """Query helpers for Department."""

    @staticmethod
    def alive(company_id) -> QuerySet[Department]:
        """Return active departments for a company, ordered by name."""
        return (
            Department.objects.for_company(company_id)
            .alive()
            .order_by("name")
        )

    @staticmethod
    def with_children(company_id) -> QuerySet[Department]:
        """
        Return active departments prefetching direct children.
        Useful for building an org-chart tree.
        """
        return (
            Department.objects.for_company(company_id)
            .alive()
            .filter(parent__isnull=True)
            .prefetch_related("children__children")
            .order_by("name")
        )

    @staticmethod
    def root_departments(company_id) -> QuerySet[Department]:
        """Return top-level departments (no parent) for a company."""
        return (
            Department.objects.for_company(company_id)
            .alive()
            .filter(parent__isnull=True)
            .order_by("name")
        )

    @staticmethod
    def children_of(parent_id: str, company_id) -> QuerySet[Department]:
        """Return direct children of a department."""
        return (
            Department.objects.for_company(company_id)
            .alive()
            .filter(parent_id=parent_id)
            .order_by("name")
        )


class PositionSelector:
    """Query helpers for Position."""

    @staticmethod
    def alive(company_id) -> QuerySet[Position]:
        """Return active positions for a company, ordered by department then title."""
        return (
            Position.objects.for_company(company_id)
            .alive()
            .select_related("department")
            .order_by("department__name", "title")
        )

    @staticmethod
    def for_department(department_id: str, company_id) -> QuerySet[Position]:
        """Return active positions within a specific department."""
        return (
            Position.objects.for_company(company_id)
            .alive()
            .filter(department_id=department_id)
            .select_related("department")
            .order_by("title")
        )

    @staticmethod
    def by_level(
        company_id, level: str | None = None, levels: list[str] | None = None
    ) -> QuerySet[Position]:
        """Return positions filtered by level(s)."""
        qs = Position.objects.for_company(company_id).alive().select_related("department")
        if levels:
            qs = qs.filter(level__in=levels)
        elif level:
            qs = qs.filter(level=level)
        return qs.order_by("department__name", "title")
