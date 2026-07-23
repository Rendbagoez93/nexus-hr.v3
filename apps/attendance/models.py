"""
apps/attendance/models.py

Attendance & Leave module — all data shape for shifts, attendance logs,
leave types/requests/balances, sites/projects, and disputes.

Layering: this file is **data shape only** — fields, constraints, simple
properties. Read queries live in ``selectors.py``, write logic in
``services.py``. Any ``if`` that encodes a business rule belongs there.

All tenant-scoped models inherit from ``apps.shared.models.TenantModel``,
which provides:
    - ``company`` FK to Company (CASCADE) — tenant isolation enforced at DB.
    - ``is_active`` / ``deleted_at`` / ``deactivate()`` — soft delete.
    - ``created_at`` / ``updated_at`` — timestamps.

``Shift`` and ``LeaveType`` are soft-deletable (already inherited via
TenantModel → SoftDeleteMixin). ``AttendanceLog``, ``LeaveRequest``,
``LeaveBalance`` and the assignment tables preserve history via FK on_delete
choices and never soft-delete; assignment records use the "open row" pattern
(effective_until IS NULL = currently active), enforced by partial unique
constraints.

Import direction: attendance imports ``companies``, ``shared``; it must NOT
import ``employees`` at module top-level — references to ``Employee`` go
through string FK labels, per the one-way import rule.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.shared.mixins.soft_delete import SoftDeleteMixin
from apps.shared.mixins.timestamped import TimestampedModel
from apps.shared.models import TenantManager, TenantModel


# ─────────────────────────────────────────────────────────────────────────────
# Status enums (TextChoices)
#
# Defined here so models.py is self-contained; services/selectors/serializers
# import from ``apps.attendance.models`` (or a future ``choices.py`` once
# extracted). Values are lowercase strings — match DB rows exactly.
# ─────────────────────────────────────────────────────────────────────────────


class AttendanceStatus(models.TextChoices):
    """Derived daily attendance status, written by ``compute_daily_attendance_status``."""

    PRESENT = "present", "Present"
    ABSENT = "absent", "Absent"
    LATE = "late", "Late"
    HALF_DAY = "half_day", "Half Day"
    ON_LEAVE = "on_leave", "On Leave"
    PENDING = "pending", "Pending"


class LeaveStatus(models.TextChoices):
    """Lifecycle of a leave request."""

    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"


class DisputeStatus(models.TextChoices):
    """Lifecycle of an attendance dispute raised by an employee."""

    OPEN = "open", "Open"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class SiteStatus(models.TextChoices):
    """Lifecycle of a site (geofence-bound location)."""

    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class ProjectStatus(models.TextChoices):
    """Lifecycle of a project (organizational grouping on top of a site)."""

    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


# ─────────────────────────────────────────────────────────────────────────────
# Shifts
# ─────────────────────────────────────────────────────────────────────────────


class ShiftQuerySet(models.QuerySet):
    """QuerySet for Shift — tenant-scoped + soft-delete-aware."""

    def for_company(self, company_id) -> "ShiftQuerySet":
        return self.filter(company_id=company_id)

    def alive(self) -> "ShiftQuerySet":
        return self.filter(is_active=True)


class ShiftManager(models.Manager):
    """Manager exposing ``.for_company()`` and ``.alive()``."""

    def get_queryset(self) -> ShiftQuerySet:
        return ShiftQuerySet(self.model, using=self._db)

    def for_company(self, company_id) -> ShiftQuerySet:
        return self.get_queryset().for_company(company_id)

    def alive(self) -> ShiftQuerySet:
        return self.get_queryset().alive()


class Shift(TenantModel):
    """
    A named work shift (e.g. "Day Shift 09:00–17:00").

    Soft-deletable: a deleted shift remains reachable by ``AttendanceLog``
    via ``on_delete=SET_NULL`` so historical logs are not destroyed when a
    shift is retired. Uniqueness of ``(company, name)`` is enforced only
    among non-deleted rows (partial unique constraint) so a name can be
    reused after soft-delete.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()

    objects = ShiftManager()

    class Meta:
        db_table = "attendance_shift"
        ordering = ["company_id", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_attendance_shift_company_name",
            ),
        ]
        indexes = [
            models.Index(
                fields=["company", "is_active"],
                name="idx_attendance_shift_company_active",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.start_time:%H:%M}–{self.end_time:%H:%M})"


class ShiftAssignment(TenantModel):
    """
    Assigns an Employee to a Shift over a date range.

    The "open row" pattern: ``effective_until IS NULL`` means the assignment
    is currently active. The partial unique constraint
    ``uq_attendance_shiftassign_emp_open`` guarantees at most one open row
    per employee — services auto-close the prior open row when assigning a
    new shift.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="shift_assignments",
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)

    objects = TenantManager()

    class Meta:
        db_table = "attendance_shift_assignment"
        ordering = ["-effective_from"]
        constraints = [
            # Only one currently-active (open) assignment per employee.
            models.UniqueConstraint(
                fields=["employee"],
                condition=models.Q(effective_until__isnull=True),
                name="uq_attendance_shiftassign_emp_open",
            ),
        ]
        indexes = [
            models.Index(
                fields=["employee", "effective_from"],
                name="idx_attendance_shiftassign_emp_from",
            ),
        ]

    def __str__(self) -> str:
        until = self.effective_until.isoformat() if self.effective_until else "open"
        return f"{self.employee_id} → {self.shift_id} ({self.effective_from} → {until})"

    @property
    def is_open(self) -> bool:
        """True when this assignment is the currently-active one."""
        return self.effective_until is None


# ─────────────────────────────────────────────────────────────────────────────
# Attendance logs
# ─────────────────────────────────────────────────────────────────────────────


class AttendanceLogQuerySet(models.QuerySet):
    """QuerySet for AttendanceLog — tenant-scoped."""

    def for_company(self, company_id) -> "AttendanceLogQuerySet":
        return self.filter(company_id=company_id)

    def for_employee(self, employee_id) -> "AttendanceLogQuerySet":
        return self.filter(employee_id=employee_id)

    def on_date(self, work_date) -> "AttendanceLogQuerySet":
        return self.filter(work_date=work_date)

    def open(self) -> "AttendanceLogQuerySet":
        """Logs clocked-in but not yet clocked-out."""
        return self.filter(clock_in_at__isnull=False, clock_out_at__isnull=True)


class AttendanceLogManager(models.Manager):
    """Manager exposing tenant-scoped lookups for AttendanceLog."""

    def get_queryset(self) -> AttendanceLogQuerySet:
        return AttendanceLogQuerySet(self.model, using=self._db)

    def for_company(self, company_id) -> AttendanceLogQuerySet:
        return self.get_queryset().for_company(company_id)

    def for_employee(self, employee_id) -> AttendanceLogQuerySet:
        return self.get_queryset().for_employee(employee_id)

    def on_date(self, work_date) -> AttendanceLogQuerySet:
        return self.get_queryset().on_date(work_date)

    def open(self) -> AttendanceLogQuerySet:
        return self.get_queryset().open()


class AttendanceLog(TenantModel):
    """
    One row per employee per work_date.

    Captures the clock-in/out events for a single working day, including
    GPS coords, photo storage keys (URLs are signed on read), the resolved
    shift and site at clock-in, and overtime computed at clock-out.

    Invariants
    ----------
    - ``(employee, work_date)`` is unique — one log per employee per day.
      Second clock-in of the day updates the same row (idempotent).
    - Photo keys are storage object keys (e.g. S3), never public URLs.
    - ``is_corrected`` is set by ``correct_attendance`` (HR-only mechanic);
      the daily-status task skips corrected logs.
    - ``total_overtime_hours`` is computed in services via Decimal math
      and rounded to ``OVERTIME_ROUNDING`` (in constants).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="attendance_logs",
    )
    work_date = models.DateField()
    clock_in_at = models.DateTimeField(null=True, blank=True)
    clock_out_at = models.DateTimeField(null=True, blank=True)

    # GPS — Decimal end-to-end (no float) for geofence math.
    clock_in_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    clock_in_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    clock_out_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    clock_out_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Storage object keys (not URLs). Signed at read time.
    clock_in_photo_key = models.CharField(max_length=512, blank=True, default="")
    clock_out_photo_key = models.CharField(max_length=512, blank=True, default="")

    # Resolved-at-clock-in references; SET_NULL so historical logs survive
    # shift/site deletion.
    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_logs",
    )
    site = models.ForeignKey(
        "attendance.Site",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_logs",
    )

    status = models.CharField(
        max_length=16,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PENDING,
    )
    is_offline_sync = models.BooleanField(default=False)
    total_overtime_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(0)],
    )
    is_corrected = models.BooleanField(default=False)

    objects = AttendanceLogManager()

    class Meta:
        db_table = "attendance_log"
        ordering = ["-work_date", "employee_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "work_date"],
                name="uq_attendance_log_emp_date",
            ),
        ]
        indexes = [
            models.Index(
                fields=["company", "work_date"],
                name="idx_attendance_log_company_date",
            ),
            models.Index(
                fields=["employee", "work_date"],
                name="idx_attendance_log_emp_date",
            ),
            models.Index(
                fields=["status"],
                name="idx_attendance_log_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.employee_id} @ {self.work_date} [{self.status}]"

    @property
    def is_open(self) -> bool:
        """True when clocked-in but not yet clocked-out today."""
        return self.clock_in_at is not None and self.clock_out_at is None


# ─────────────────────────────────────────────────────────────────────────────
# Leave types, requests, balances
# ─────────────────────────────────────────────────────────────────────────────


class LeaveType(TenantModel):
    """
    A category of leave (Annual, Sick, Unpaid, …).

    Soft-deletable. ``default_days`` seeds new ``LeaveBalance`` rows when an
    employee is created (``initialize_leave_balances``). Uniqueness of
    ``(company, name)`` is enforced only among non-deleted rows.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    default_days = models.PositiveIntegerField(default=12)
    carry_over_allowed = models.BooleanField(default=False)

    objects = TenantManager()

    class Meta:
        db_table = "attendance_leave_type"
        ordering = ["company_id", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_attendance_leavetype_company_name",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class LeaveRequestQuerySet(models.QuerySet):
    """QuerySet for LeaveRequest — tenant-scoped."""

    def for_company(self, company_id) -> "LeaveRequestQuerySet":
        return self.filter(company_id=company_id)

    def for_employee(self, employee_id) -> "LeaveRequestQuerySet":
        return self.filter(employee_id=employee_id)

    def pending(self) -> "LeaveRequestQuerySet":
        return self.filter(status=LeaveStatus.PENDING)


class LeaveRequestManager(models.Manager):
    """Manager exposing tenant-scoped lookups for LeaveRequest."""

    def get_queryset(self) -> LeaveRequestQuerySet:
        return LeaveRequestQuerySet(self.model, using=self._db)

    def for_company(self, company_id) -> LeaveRequestQuerySet:
        return self.get_queryset().for_company(company_id)

    def for_employee(self, employee_id) -> LeaveRequestQuerySet:
        return self.get_queryset().for_employee(employee_id)

    def pending(self) -> LeaveRequestQuerySet:
        return self.get_queryset().pending()


class LeaveRequest(TenantModel):
    """
    A request for leave, pending approval.

    Invariants
    ----------
    - ``end_date >= start_date`` is enforced at the DB level
      (``ck_attendance_leavereq_date_order``).
    - ``approved_by`` and ``resolved_by`` use SET_NULL so historical
      references survive user/employee deletion.
    - Balance deduction happens in ``approve_leave_request`` inside a
      ``select_for_update`` transaction — see services.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="leave_requests",
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="leave_requests",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=LeaveStatus.choices,
        default=LeaveStatus.PENDING,
    )
    approved_by = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leaves",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")

    objects = LeaveRequestManager()

    class Meta:
        db_table = "attendance_leave_request"
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="ck_attendance_leavereq_date_order",
            ),
        ]
        indexes = [
            models.Index(
                fields=["employee", "status"],
                name="idx_attendance_leavereq_emp_status",
            ),
            models.Index(
                fields=["company", "status"],
                name="idx_attendance_leavereq_company_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.employee_id} {self.start_date}→{self.end_date} [{self.status}]"

    @property
    def requested_days(self) -> int:
        """Inclusive calendar days (start_date and end_date both count)."""
        return (self.end_date - self.start_date).days + 1


class LeaveBalanceQuerySet(models.QuerySet):
    """QuerySet for LeaveBalance — tenant-scoped via employee.company."""

    def for_company(self, company_id) -> "LeaveBalanceQuerySet":
        return self.filter(employee__company_id=company_id)

    def for_employee(self, employee_id) -> "LeaveBalanceQuerySet":
        return self.filter(employee_id=employee_id)

    def for_year(self, year: int) -> "LeaveBalanceQuerySet":
        return self.filter(year=year)


class LeaveBalanceManager(models.Manager):
    """Manager exposing tenant-scoped lookups for LeaveBalance."""

    def get_queryset(self) -> LeaveBalanceQuerySet:
        return LeaveBalanceQuerySet(self.model, using=self._db)

    def for_company(self, company_id) -> LeaveBalanceQuerySet:
        return self.get_queryset().for_company(company_id)

    def for_employee(self, employee_id) -> LeaveBalanceQuerySet:
        return self.get_queryset().for_employee(employee_id)

    def for_year(self, year: int) -> LeaveBalanceQuerySet:
        return self.get_queryset().for_year(year)


class LeaveBalance(TenantModel):
    """
    Annual leave balance per (employee, leave_type, year).

    All day counts are ``Decimal`` to match money-class precision and to
    avoid float rounding in payroll-adjacent math.

    Invariants
    ----------
    - ``(employee, leave_type, year)`` is unique — one balance row per
      (employee, type, year).
    - ``used_days >= 0`` is enforced at the DB level
      (``ck_attendance_leavebalance_used_nonneg``); the services layer
      raises ``InsufficientLeaveBalance`` before the constraint fires.
    - ``available_days`` is a computed property, not stored.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="leave_balances",
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="balances",
    )
    year = models.PositiveIntegerField()
    quota_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    used_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    carry_over_days = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(0)],
    )

    objects = LeaveBalanceManager()

    class Meta:
        db_table = "attendance_leave_balance"
        ordering = ["-year", "employee_id", "leave_type_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "leave_type", "year"],
                name="uq_attendance_leavebalance_emp_type_year",
            ),
            models.CheckConstraint(
                condition=models.Q(used_days__gte=0),
                name="ck_attendance_leavebalance_used_nonneg",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.employee_id} {self.leave_type_id} {self.year}"

    @property
    def available_days(self) -> Decimal:
        """Quota + carry-over - used. Can be negative if balance is overdrawn."""
        return self.quota_days + self.carry_over_days - self.used_days


# ─────────────────────────────────────────────────────────────────────────────
# Sites & projects (geofence override layer)
# ─────────────────────────────────────────────────────────────────────────────


class SiteQuerySet(models.QuerySet):
    """QuerySet for Site — tenant-scoped."""

    def for_company(self, company_id) -> "SiteQuerySet":
        return self.filter(company_id=company_id)

    def active(self) -> "SiteQuerySet":
        return self.filter(status=SiteStatus.ACTIVE)


class SiteManager(models.Manager):
    """Manager exposing tenant-scoped lookups for Site."""

    def get_queryset(self) -> SiteQuerySet:
        return SiteQuerySet(self.model, using=self._db)

    def for_company(self, company_id) -> SiteQuerySet:
        return self.get_queryset().for_company(company_id)

    def active(self) -> SiteQuerySet:
        return self.get_queryset().active()


class Site(TenantModel):
    """
    A physical site (office, yard, mine face, construction site) where
    employees clock in/out. A site may override the company-wide geofence
    radius via ``geofence_radius_meters``; when an employee has an active
    ``SiteAssignment`` at clock-in, the site geofence is used in place of
    the company geofence (see ``validators.GeofenceValidator``).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=32)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    geofence_radius_meters = models.PositiveIntegerField(default=100)
    status = models.CharField(
        max_length=16,
        choices=SiteStatus.choices,
        default=SiteStatus.ACTIVE,
    )

    objects = SiteManager()

    class Meta:
        db_table = "attendance_site"
        ordering = ["company_id", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_attendance_site_company_code",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Project(TenantModel):
    """
    An organizational project grouping on top of a site (optional).

    Projects are independent of geofencing — they exist for project-based
    attendance reporting. A project may optionally belong to a site.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=32)
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="projects",
    )
    status = models.CharField(
        max_length=16,
        choices=ProjectStatus.choices,
        default=ProjectStatus.ACTIVE,
    )

    objects = TenantManager()

    class Meta:
        db_table = "attendance_project"
        ordering = ["company_id", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_attendance_project_company_code",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class SiteAssignment(TenantModel):
    """
    Assigns an Employee to a Site over a date range (the "open row" pattern).

    ``effective_until IS NULL`` = currently active. The partial unique
    constraint ``uq_attendance_siteassign_emp_open`` guarantees at most
    one open row per employee; services auto-close the prior open row
    when assigning a new site.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="site_assignments",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)

    objects = TenantManager()

    class Meta:
        db_table = "attendance_site_assignment"
        ordering = ["-effective_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee"],
                condition=models.Q(effective_until__isnull=True),
                name="uq_attendance_siteassign_emp_open",
            ),
        ]
        indexes = [
            models.Index(
                fields=["site", "effective_from"],
                name="idx_attendance_siteassign_site_from",
            ),
        ]

    def __str__(self) -> str:
        until = self.effective_until.isoformat() if self.effective_until else "open"
        return f"{self.employee_id} → {self.site_id} ({self.effective_from} → {until})"

    @property
    def is_open(self) -> bool:
        return self.effective_until is None


class ProjectAssignment(TenantModel):
    """
    Assigns an Employee to a Project over a date range (the "open row" pattern).

    An employee may be assigned to **one** open project at a time across the
    company — the partial unique constraint enforces this. If an employee
    is to be on multiple concurrent projects, model the split in services
    (splitting time) or relax this constraint in a follow-up migration.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="project_assignments",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)

    objects = TenantManager()

    class Meta:
        db_table = "attendance_project_assignment"
        ordering = ["-effective_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "project"],
                condition=models.Q(effective_until__isnull=True),
                name="uq_attendance_projectassign_emp_project_open",
            ),
        ]

    def __str__(self) -> str:
        until = self.effective_until.isoformat() if self.effective_until else "open"
        return f"{self.employee_id} → {self.project_id} ({self.effective_from} → {until})"

    @property
    def is_open(self) -> bool:
        return self.effective_until is None


# ─────────────────────────────────────────────────────────────────────────────
# Attendance disputes
# ─────────────────────────────────────────────────────────────────────────────


class AttendanceDisputeQuerySet(models.QuerySet):
    """QuerySet for AttendanceDispute — tenant-scoped."""

    def for_company(self, company_id) -> "AttendanceDisputeQuerySet":
        return self.filter(company_id=company_id)

    def open(self) -> "AttendanceDisputeQuerySet":
        return self.filter(status=DisputeStatus.OPEN)


class AttendanceDisputeManager(models.Manager):
    """Manager exposing tenant-scoped lookups for AttendanceDispute."""

    def get_queryset(self) -> AttendanceDisputeQuerySet:
        return AttendanceDisputeQuerySet(self.model, using=self._db)

    def for_company(self, company_id) -> AttendanceDisputeQuerySet:
        return self.get_queryset().for_company(company_id)

    def open(self) -> AttendanceDisputeQuerySet:
        return self.get_queryset().open()


class AttendanceDispute(TenantModel):
    """
    A dispute raised by an employee against an ``AttendanceLog``.

    The dispute references — and can correct — a single attendance log.
    Approval reuses ``correct_attendance`` on the underlying log with the
    corrected values supplied by the approver; rejection is a no-op on the
    log. This keeps the dispute flow auditable through the same HR-correct
    code path.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attendance_log = models.ForeignKey(
        AttendanceLog,
        on_delete=models.PROTECT,
        related_name="disputes",
    )
    raised_by = models.ForeignKey(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="raised_disputes",
    )
    reason = models.TextField()
    evidence_photo_key = models.CharField(max_length=512, blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=DisputeStatus.choices,
        default=DisputeStatus.OPEN,
    )
    resolved_by = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_disputes",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True, default="")

    objects = AttendanceDisputeManager()

    class Meta:
        db_table = "attendance_dispute"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["company", "status"],
                name="idx_attendance_dispute_company_status",
            ),
        ]

    def __str__(self) -> str:
        return f"dispute {self.id} on log {self.attendance_log_id} [{self.status}]"