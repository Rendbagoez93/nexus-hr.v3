"""
apps/departments/services/department_service.py

Business logic for Department CRUD operations.
All methods are company-scoped (tenant isolation enforced).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from apps.departments.exceptions import DepartmentError
from apps.departments.models import Department

if TYPE_CHECKING:
    from uuid import UUID


class DepartmentService:
    """Handles Department operations for a given company."""

    @staticmethod
    def list_for_company(
        company_id: UUID,
        parent_id: UUID | None = None,
        is_active: bool = True,
    ) -> list[Department]:
        """List departments optionally filtered by parent and active status."""
        qs = Department.objects.for_company(company_id)
        if is_active:
            qs = qs.alive()
        if parent_id is not None:
            qs = qs.filter(parent_id=parent_id)
        elif parent_id is None and is_active:
            pass
        return list(qs.order_by("name"))

    @staticmethod
    def get_by_id(pk: UUID, company_id: UUID) -> Department:
        """Fetch a single department, enforcing company boundary."""
        try:
            return Department.objects.for_company(company_id).get(pk=pk)
        except Department.DoesNotExist:
            raise DepartmentError(detail="Department not found.", status_code=404)

    @staticmethod
    @transaction.atomic
    def create(
        company_id: UUID,
        name: str,
        code: str,
        parent_id: UUID | None = None,
        created_by: str | None = None,
    ) -> Department:
        """Create a new department within the company."""
        parent = None
        if parent_id:
            try:
                parent = Department.objects.for_company(company_id).get(pk=parent_id)
            except Department.DoesNotExist:
                raise DepartmentError(detail="Parent department not found.", status_code=404)

        department = Department(
            company_id=company_id,
            name=name,
            code=code.upper(),
            parent=parent,
        )
        department.save()
        return department

    @staticmethod
    @transaction.atomic
    def update(
        pk: UUID,
        company_id: UUID,
        **fields,
    ) -> Department:
        """Update a department's fields."""
        department = DepartmentService.get_by_id(pk, company_id)

        for field_name, value in fields.items():
            if field_name == "code" and value is not None:
                value = value.upper()
            if field_name == "parent_id" and value is None:
                department.parent = None
            elif value is not None and hasattr(department, field_name):
                setattr(department, field_name, value)

        department.save()
        return department

    @staticmethod
    @transaction.atomic
    def soft_delete(pk: UUID, company_id: UUID) -> Department:
        """Soft-delete a department."""
        department = DepartmentService.get_by_id(pk, company_id)
        department.deactivate()
        return department

    @staticmethod
    @transaction.atomic
    def restore(pk: UUID, company_id: UUID) -> Department:
        """Restore a soft-deleted department."""
        try:
            department = Department.objects.for_company(company_id).get(
                pk=pk, is_active=False
            )
        except Department.DoesNotExist:
            raise DepartmentError(detail="Department not found or already active.", status_code=404)
        department.restore()
        return department
