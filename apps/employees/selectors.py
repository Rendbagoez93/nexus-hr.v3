"""
apps/employees/selectors.py

Query helpers for Employee.
"""

from django.db.models import QuerySet

from apps.employees.models import Employee


class EmployeeSelector:
    """Query helpers for Employee."""

    @staticmethod
    def alive(company_id) -> QuerySet[Employee]:
        """Return active employees for a company, ordered by emp_number."""
        return (
            Employee.objects.for_company(company_id)
            .alive()
            .select_related("department", "position", "direct_manager")
            .order_by("emp_number")
        )

    @staticmethod
    def active(company_id) -> QuerySet[Employee]:
        """Return billable (status=active AND is_active=True) employees for a company."""
        return (
            Employee.objects.for_company(company_id)
            .active()
            .select_related("department", "position", "direct_manager")
            .order_by("emp_number")
        )

    @staticmethod
    def for_department(department_id, company_id) -> QuerySet[Employee]:
        """Return employees in a specific department."""
        return (
            Employee.objects.for_company(company_id)
            .alive()
            .filter(department_id=department_id)
            .select_related("department", "position", "direct_manager")
            .order_by("emp_number")
        )

    @staticmethod
    def for_manager(manager_id, company_id) -> QuerySet[Employee]:
        """Return direct reports of a manager."""
        return (
            Employee.objects.for_company(company_id)
            .alive()
            .filter(direct_manager_id=manager_id)
            .select_related("department", "position", "direct_manager")
            .order_by("emp_number")
        )
