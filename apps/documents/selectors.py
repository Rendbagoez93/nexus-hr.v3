"""
apps/documents/selectors.py

Query helpers for EmployeeDocument.
"""

from django.db.models import QuerySet

from apps.documents.models import EmployeeDocument


class DocumentSelector:
    """Query helpers for EmployeeDocument, scoped through employee.company."""

    @staticmethod
    def for_employee(employee_id, company_id) -> QuerySet[EmployeeDocument]:
        """Return active documents for an employee, scoped to the employee's company."""
        return (
            EmployeeDocument.objects.for_company(company_id)
            .for_employee(employee_id)
            .alive()
            .select_related("employee")
            .order_by("-created_at")
        )
