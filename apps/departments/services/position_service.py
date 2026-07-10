"""
apps/departments/services/position_service.py

Business logic for Position CRUD operations.
All methods are company-scoped (tenant isolation enforced).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction

from apps.departments.exceptions import PositionError
from apps.departments.models import Department, Position

if TYPE_CHECKING:
    from uuid import UUID


class PositionService:
    """Handles Position operations for a given company."""

    @staticmethod
    def list_for_company(
        company_id: UUID,
        department_id: UUID | None = None,
        level: str | None = None,
        is_active: bool = True,
    ) -> list[Position]:
        """List positions optionally filtered by department and level."""
        qs = Position.objects.for_company(company_id)
        if is_active:
            qs = qs.alive()
        if department_id:
            qs = qs.filter(department_id=department_id)
        if level:
            qs = qs.filter(level=level)
        return list(qs.select_related("department").order_by("department__name", "title"))

    @staticmethod
    def get_by_id(pk: UUID, company_id: UUID) -> Position:
        """Fetch a single position, enforcing company boundary."""
        try:
            return Position.objects.for_company(company_id).get(pk=pk)
        except Position.DoesNotExist:
            raise PositionError(detail="Position not found.", status_code=404)

    @staticmethod
    @transaction.atomic
    def create(
        company_id: UUID,
        department_id: UUID,
        title: str,
        level: str,
        base_salary_min: Decimal,
        base_salary_max: Decimal,
        created_by: str | None = None,
    ) -> Position:
        """Create a new position within the company and department."""
        if base_salary_min > base_salary_max:
            raise PositionError(
                detail="base_salary_min cannot be greater than base_salary_max.",
            )

        try:
            department = Department.objects.for_company(company_id).get(pk=department_id)
        except Department.DoesNotExist:
            raise PositionError(detail="Department not found.", status_code=404)

        position = Position(
            company_id=company_id,
            department=department,
            title=title,
            level=level,
            base_salary_min=base_salary_min,
            base_salary_max=base_salary_max,
        )
        position.save()
        return position

    @staticmethod
    @transaction.atomic
    def update(
        pk: UUID,
        company_id: UUID,
        **fields,
    ) -> Position:
        """Update a position's fields, validating salary range."""
        if "base_salary_min" in fields and "base_salary_max" in fields:
            min_val = fields["base_salary_min"]
            max_val = fields["base_salary_max"]
            if min_val is not None and max_val is not None and min_val > max_val:
                raise PositionError(
                    detail="base_salary_min cannot be greater than base_salary_max.",
                )
        elif "base_salary_min" in fields and fields["base_salary_min"] is not None:
            pos = PositionService.get_by_id(pk, company_id)
            if fields["base_salary_min"] > pos.base_salary_max:
                raise PositionError(
                    detail="base_salary_min cannot be greater than base_salary_max.",
                )
        elif "base_salary_max" in fields and fields["base_salary_max"] is not None:
            pos = PositionService.get_by_id(pk, company_id)
            if pos.base_salary_min > fields["base_salary_max"]:
                raise PositionError(
                    detail="base_salary_min cannot be greater than base_salary_max.",
                )

        if "department_id" in fields and fields["department_id"]:
            try:
                department = Department.objects.for_company(company_id).get(
                    pk=fields["department_id"]
                )
                fields["department"] = department
                del fields["department_id"]
            except Department.DoesNotExist:
                raise PositionError(detail="Department not found.", status_code=404)
        elif "department_id" in fields:
            del fields["department_id"]

        position = PositionService.get_by_id(pk, company_id)
        for field_name, value in fields.items():
            if value is not None and hasattr(position, field_name):
                setattr(position, field_name, value)
        position.save()
        return position

    @staticmethod
    @transaction.atomic
    def soft_delete(pk: UUID, company_id: UUID) -> Position:
        """Soft-delete a position."""
        position = PositionService.get_by_id(pk, company_id)
        position.deactivate()
        return position

    @staticmethod
    @transaction.atomic
    def restore(pk: UUID, company_id: UUID) -> Position:
        """Restore a soft-deleted position."""
        try:
            position = Position.objects.for_company(company_id).get(pk=pk, is_active=False)
        except Position.DoesNotExist:
            raise PositionError(detail="Position not found or already active.", status_code=404)
        position.restore()
        return position
