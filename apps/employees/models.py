"""
apps/employees/models.py

Employee — the central entity of Nexus HR.

Employee is tenant-scoped (via company FK), links to AuthUser (optional),
and carries all personal and employment data for billing-relevant active status.
"""

import re
import uuid

from django.core.validators import MinValueValidator
from django.db import models

from apps.companies.models import Company
from apps.departments.models import Department, Position
from apps.shared.mixins.soft_delete import SoftDeleteMixin
from apps.shared.mixins.timestamped import TimestampedModel
from apps.shared.models import TenantManager
from apps.users.models import AuthUser
from apps.employees.choices import EmployeeStatus, EmploymentType, Gender


class EmployeeQuerySet(models.QuerySet):
    """QuerySet for Employee with convenience filters."""

    def for_company(self, company_id: int) -> "EmployeeQuerySet":
        return self.filter(company_id=company_id)

    def alive(self) -> "EmployeeQuerySet":
        return self.filter(is_active=True)

    def active(self) -> "EmployeeQuerySet":
        """Employees that count toward billing (status=active)."""
        return self.filter(status=EmployeeStatus.ACTIVE, is_active=True)


class EmployeeManager(TenantManager):
    """Custom manager for Employee."""

    def get_queryset(self) -> EmployeeQuerySet:
        return EmployeeQuerySet(self.model, using=self._db)

    def for_company(self, company_id: int) -> EmployeeQuerySet:
        return self.get_queryset().for_company(company_id)

    def alive(self) -> EmployeeQuerySet:
        return self.get_queryset().alive()

    def active(self) -> EmployeeQuerySet:
        return self.get_queryset().active()


class Employee(SoftDeleteMixin, TimestampedModel):
    """
    The central entity of Nexus HR.

    Represents an employee within a Company, linked optionally to an AuthUser
    for dashboard/mobile access. All personal, employment, and compliance fields
    live here. Billing-relevant "active" status is ``status=active`` AND
    ``is_active=True``.

    Attributes
    ----------
    company : Company
        Tenant — the company this employee belongs to.
    user : AuthUser | None
        Optional link to the employee's login account.
    emp_number : str
        Auto-generated, unique per company in NXS-0001 format.
    personal fields
        first_name, last_name, email, phone, etc.
    employment fields
        department, position, status, employment_type, join_date, resign_date, etc.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="employees",
        db_index=True,
    )
    user = models.OneToOneField(
        AuthUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_profile",
    )

    # --- Identification ---
    emp_number = models.CharField(max_length=20, unique=True, db_index=True)

    # --- Personal Info ---
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, db_index=True)
    phone = models.CharField(max_length=20, blank=True, default="")
    mobile_phone = models.CharField(max_length=20, blank=True, default="")
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        default=Gender.OTHER,
    )
    date_of_birth = models.DateField(null=True, blank=True)
    place_of_birth = models.CharField(max_length=100, blank=True, default="")

    # --- Address ---
    id_card_address = models.TextField(blank=True, default="")
    residential_address = models.TextField(blank=True, default="")

    # --- Employment Info ---
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="employees",
        null=True,
        blank=True,
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name="employees",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=EmployeeStatus.choices,
        default=EmployeeStatus.ACTIVE,
        db_index=True,
    )
    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.PERMANENT,
    )
    join_date = models.DateField(db_index=True)
    resign_date = models.DateField(null=True, blank=True)
    termination_date = models.DateField(null=True, blank=True)
    termination_reason = models.TextField(blank=True, default="")

    # --- Salary ---
    base_salary = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
    )

    # --- Manager Link ---
    direct_manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_reports",
    )

    objects = EmployeeManager()

    class Meta:
        db_table = "employees_employee"
        ordering = ["emp_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "emp_number"],
                name="uq_employees_company_emp_number",
            ),
        ]
        indexes = [
            models.Index(
                fields=["company", "status"],
                name="idx_emp_comp_status",
            ),
            models.Index(
                fields=["company", "department"],
                name="idx_emp_comp_dept",
            ),
            models.Index(
                fields=["company", "is_active"],
                name="idx_emp_comp_active",
            ),
            models.Index(
                fields=["email"],
                name="idx_emp_email",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.emp_number})"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_billable(self) -> bool:
        """True when this employee counts toward billing."""
        return self.status == EmployeeStatus.ACTIVE and self.is_active

    @property
    def is_active_employment(self) -> bool:
        """True when the employee is in an active employment state."""
        return self.status == EmployeeStatus.ACTIVE
