"""
apps/departments/models.py

Department and Position models.
Both are tenant-scoped via TenantModel (company FK).
"""

import uuid

from django.core.validators import MinValueValidator
from django.db import models

from apps.shared.mixins.soft_delete import SoftDeleteMixin
from apps.shared.mixins.timestamped import TimestampedModel
from apps.shared.models import TenantManager


class Department(SoftDeleteMixin, TimestampedModel):
    """
    Represents a department within a Company.

    Supports a hierarchical org-chart via self-referencing parent FK.
    Departments are uniquely identified by code within a company.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="departments",
        db_index=True,
    )
    code = models.CharField(
        max_length=20,
        db_index=True,
    )
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        db_index=True,
    )

    objects = TenantManager()

    class Meta:
        db_table = "departments_department"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_departments_company_code",
            ),
        ]
        indexes = [
            models.Index(
                fields=["company", "is_active"],
                name="idx_dept_comp_active",
            ),
            models.Index(
                fields=["company", "parent"],
                name="idx_dept_comp_parent",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Position(SoftDeleteMixin, TimestampedModel):
    """
    Represents a job position within a Department.

    Each position belongs to a company and a department, with a defined
    job level and salary band (min/max). The salary band constraint
    (min <= max) is enforced at the database level.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="positions",
        db_index=True,
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="positions",
        db_index=True,
    )
    title = models.CharField(max_length=255, db_index=True)
    level = models.CharField(max_length=20, db_index=True)
    base_salary_min = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    base_salary_max = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    objects = TenantManager()

    class Meta:
        db_table = "departments_position"
        ordering = ["department", "level", "title"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(base_salary_min__lte=models.F("base_salary_max")),
                name="ck_positions_salary_min_lte_max",
            ),
        ]
        indexes = [
            models.Index(
                fields=["company", "is_active"],
                name="idx_pos_comp_active",
            ),
            models.Index(
                fields=["company", "department"],
                name="idx_pos_comp_dept",
            ),
            models.Index(
                fields=["company", "level"],
                name="idx_pos_comp_level",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.level})"
