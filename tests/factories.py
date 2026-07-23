"""
tests/factories.py — factory-boy factories for all Phase 1–3 models.

Usage: from tests.factories import CompanyFactory, HRAdminFactory, etc.
Never use Model.objects.create() in tests — use factories instead.

Scope notes:
  - CompanyFactory, SubscriptionPlanFactory: module scope eligible (read-only ref data)
  - All user factories: function scope (tests mutate/create users)
  - DepartmentFactory, PositionFactory: function scope (stub models)
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

import factory
from django.contrib.auth.hashers import make_password
from django.utils import timezone

if TYPE_CHECKING:
    from apps.companies.models import Company, CompanySubscription, SubscriptionPlan
    from apps.departments.models import Department, Position
    from apps.employees.models import Employee
    from apps.users.models import AuthUser
    from apps.attendance.models import (  # noqa: F401  (used by factories below)
        AttendanceDispute,
        AttendanceLog,
        LeaveBalance,
        LeaveRequest,
        LeaveType,
        Project,
        ProjectAssignment,
        Shift,
        ShiftAssignment,
        Site,
        SiteAssignment,
    )


# ---------------------------------------------------------------------------
# Company factories
# ---------------------------------------------------------------------------

class CompanyFactory(factory.django.DjangoModelFactory):
    """Factory for Company — each call creates a unique company."""

    class Meta:
        model = "companies.Company"

    name = factory.Sequence(lambda n: f"Company {n}")
    industry = "manufacturing"
    subscription_tier = "core"
    is_active = True
    emp_number_prefix = factory.Sequence(lambda n: f"PFX{n:02d}")
    geofence_radius_meters = 100


class SubscriptionPlanFactory(factory.django.DjangoModelFactory):
    """Factory for SubscriptionPlan — feature-gated plan definitions."""

    class Meta:
        model = "companies.SubscriptionPlan"

    name = factory.Sequence(lambda n: f"Plan {n}")
    code = factory.Sequence(lambda n: f"plan_{n}")
    has_attendance = False
    has_hse = False
    has_payroll = False
    price_per_employee_per_month = factory.Faker(
        "pydecimal", left_digits=6, right_digits=2, positive=True
    )
    is_active = True


class CompanySubscriptionFactory(factory.django.DjangoModelFactory):
    """Factory for CompanySubscription — links Company to SubscriptionPlan."""

    class Meta:
        model = "companies.CompanySubscription"

    company = factory.SubFactory(CompanyFactory)
    plan = factory.SubFactory(SubscriptionPlanFactory)
    billing_period_start = date.today().replace(day=1)
    billing_period_end = (date.today().replace(day=1) + timedelta(days=365)).replace(
        month=1
    )
    active_employee_count = 0
    is_active = True


# ---------------------------------------------------------------------------
# Core plan factories — named fixtures for specific subscription tiers
# ---------------------------------------------------------------------------

class CorePlanFactory(SubscriptionPlanFactory):
    """SubscriptionPlan with no add-on modules (core only)."""

    name = "Core Plan"
    code = "core"
    has_attendance = False
    has_hse = False
    has_payroll = False


class AttendancePlanFactory(SubscriptionPlanFactory):
    """SubscriptionPlan with attendance module enabled."""

    name = "Attendance Plan"
    code = "attendance"
    has_attendance = True
    has_hse = False
    has_payroll = False


class HSEPlanFactory(SubscriptionPlanFactory):
    """SubscriptionPlan with HSE module enabled."""

    name = "HSE Plan"
    code = "hse"
    has_attendance = False
    has_hse = True
    has_payroll = False


class FullPlanFactory(SubscriptionPlanFactory):
    """SubscriptionPlan with all modules enabled."""

    name = "Full Suite Plan"
    code = "full"
    has_attendance = True
    has_hse = True
    has_payroll = True


# ---------------------------------------------------------------------------
# Department factories
# ---------------------------------------------------------------------------

class DepartmentFactory(factory.django.DjangoModelFactory):
    """Factory for Department."""

    class Meta:
        model = "departments.Department"

    name = factory.Sequence(lambda n: f"Department {n}")
    code = factory.Sequence(lambda n: f"DEPT{n:03d}")
    company = factory.SubFactory(CompanyFactory)


# ---------------------------------------------------------------------------
# Position factories
# ---------------------------------------------------------------------------

class PositionFactory(factory.django.DjangoModelFactory):
    """Factory for Position."""

    class Meta:
        model = "departments.Position"

    title = factory.Sequence(lambda n: f"Position {n}")
    level = "staff"
    base_salary_min = Decimal("5000000")
    base_salary_max = Decimal("8000000")
    company = factory.SubFactory(CompanyFactory)


# ---------------------------------------------------------------------------
# User factories — each creates a fresh company so tests stay isolated
# ---------------------------------------------------------------------------

class BaseUserFactory(factory.django.DjangoModelFactory):
    """Abstract base for AuthUser factories — shared password and email logic."""

    class Meta:
        model = "users.AuthUser"

    email = factory.Sequence(lambda n: f"user{n}@test.local")
    password = "TestPass123!"
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Use the manager to support custom manager logic.

        `password` is passed straight through to `create_user`/`create_superuser`,
        which already calls `set_password()` and saves once — avoiding the extra
        post-generation save that `PostGenerationMethodCall` would trigger.
        """
        manager = model_class.objects
        return manager.create_user(*args, **kwargs)


class PlatformAdminFactory(BaseUserFactory):
    """Factory for a platform admin (is_superuser=True, no company)."""

    email = factory.Sequence(lambda n: f"platform_admin{n}@nexus.local")
    role = "platform_admin"
    is_superuser = True
    is_staff = True
    company = None

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = model_class.objects
        return manager.create_superuser(*args, **kwargs)


class HRAdminFactory(BaseUserFactory):
    """Factory for an HR Admin within a company."""

    email = factory.Sequence(lambda n: f"hr_admin{n}@test.local")
    role = "hr_admin"
    company = factory.SubFactory(CompanyFactory)
    is_superuser = False
    is_staff = False


class ManagerFactory(BaseUserFactory):
    """Factory for a Manager within a company."""

    email = factory.Sequence(lambda n: f"manager{n}@test.local")
    role = "manager"
    company = factory.SubFactory(CompanyFactory)
    is_superuser = False
    is_staff = False


class EmployeeUserFactory(BaseUserFactory):
    """Factory for a plain Employee within a company."""

    email = factory.Sequence(lambda n: f"employee{n}@test.local")
    role = "employee"
    company = factory.SubFactory(CompanyFactory)
    is_superuser = False
    is_staff = False


class HSEOfficerFactory(BaseUserFactory):
    """Factory for an HSE Officer within a company."""

    email = factory.Sequence(lambda n: f"hse_officer{n}@test.local")
    role = "hse_officer"
    company = factory.SubFactory(CompanyFactory)
    is_superuser = False
    is_staff = False


# ---------------------------------------------------------------------------
# Inactive user factories — for auth negative-path tests
# ---------------------------------------------------------------------------

class InactiveUserFactory(BaseUserFactory):
    """Factory for an inactive AuthUser (is_active=False)."""

    email = factory.Sequence(lambda n: f"inactive{n}@test.local")
    is_active = False
    role = "employee"
    company = factory.SubFactory(CompanyFactory)


# ---------------------------------------------------------------------------
# Employee factories
# ---------------------------------------------------------------------------

class EmployeeFactory(factory.django.DjangoModelFactory):
    """Factory for Employee — each call creates a unique employee per company."""

    class Meta:
        model = "employees.Employee"

    company = factory.SubFactory(CompanyFactory)
    user = None
    emp_number = factory.Sequence(lambda n: f"NXS-{n:04d}")
    first_name = factory.Sequence(lambda n: f"FirstName{n}")
    last_name = factory.Sequence(lambda n: f"LastName{n}")
    email = factory.Sequence(lambda n: f"employee{n}@nexus.test")
    phone = factory.Sequence(lambda n: f"0813{n:08d}")
    mobile_phone = factory.Sequence(lambda n: f"0814{n:08d}")
    gender = "male"
    date_of_birth = "1990-01-01"
    place_of_birth = "Jakarta"
    id_card_address = factory.Sequence(lambda n: f"Address {n}, Jakarta")
    residential_address = factory.Sequence(lambda n: f"Residence {n}, Jakarta")
    department = None
    position = None
    status = "active"
    employment_type = "permanent"
    join_date = "2020-01-01"
    resign_date = None
    termination_date = None
    termination_reason = ""
    base_salary = Decimal("10000000.00")
    direct_manager = None


# ---------------------------------------------------------------------------
# Attendance module factories
#
# Each factory is keyed to its model's natural default state — a working
# employee with a known shift, an open log for today, a fresh leave
# balance for the current year. Tests that need off-default behavior
# (out-of-range GPS, expired offline timestamps, exhausted balances) set
# fields explicitly after creation; they should not mutate the factory
# defaults in a way that hides negative-path intent.
# ---------------------------------------------------------------------------

# Reference company constants for default values. Imported at module load so
# factory defaults stay in sync with the production constants used by
# services/validators — never duplicate these numbers as literals.
from apps.companies.constants import (
    DEFAULT_ANNUAL_LEAVE_DAYS,
    DEFAULT_GEOFENCE_RADIUS_METERS,
)


class ShiftFactory(factory.django.DjangoModelFactory):
    """Factory for Shift — standard 09:00–17:00 day shift."""

    class Meta:
        model = "attendance.Shift"

    company = factory.SubFactory(CompanyFactory)
    name = factory.Sequence(lambda n: f"Shift {n}")
    start_time = time(9, 0)
    end_time = time(17, 0)


class ShiftAssignmentFactory(factory.django.DjangoModelFactory):
    """Factory for ShiftAssignment — open assignment (effective_until=None)."""

    class Meta:
        model = "attendance.ShiftAssignment"

    company = factory.SelfAttribute("employee.company")
    employee = factory.SubFactory(EmployeeFactory)
    shift = factory.SubFactory(ShiftFactory)
    effective_from = factory.LazyFunction(date.today)
    effective_until = None  # open assignment


class AttendanceLogFactory(factory.django.DjangoModelFactory):
    """Factory for AttendanceLog — PENDING log for today's work_date.

    GPS defaults to a point inside a generic Jakarta office geofence
    (-6.200, 106.817). Tests asserting geofence rejection override these
    to coordinates far outside the radius.
    """

    class Meta:
        model = "attendance.AttendanceLog"

    company = factory.SelfAttribute("employee.company")
    employee = factory.SubFactory(EmployeeFactory)
    work_date = factory.LazyFunction(date.today)
    clock_in_at = None
    clock_out_at = None
    clock_in_lat = Decimal("-6.200000")
    clock_in_lng = Decimal("106.816666")
    clock_out_lat = None
    clock_out_lng = None
    clock_in_photo_key = ""
    clock_out_photo_key = ""
    shift = None
    site = None
    status = "pending"
    is_offline_sync = False
    total_overtime_hours = Decimal("0.00")
    is_corrected = False


class LeaveTypeFactory(factory.django.DjangoModelFactory):
    """Factory for LeaveType — annual leave with statutory default."""

    class Meta:
        model = "attendance.LeaveType"

    company = factory.SubFactory(CompanyFactory)
    name = factory.Sequence(lambda n: f"Leave Type {n}")
    default_days = DEFAULT_ANNUAL_LEAVE_DAYS
    carry_over_allowed = False


class LeaveRequestFactory(factory.django.DjangoModelFactory):
    """Factory for LeaveRequest — PENDING request starting today."""

    class Meta:
        model = "attendance.LeaveRequest"

    company = factory.SelfAttribute("employee.company")
    employee = factory.SubFactory(EmployeeFactory)
    leave_type = factory.SubFactory(LeaveTypeFactory)
    start_date = factory.LazyFunction(date.today)
    end_date = factory.LazyFunction(date.today)
    reason = ""
    status = "pending"
    approved_by = None
    decided_at = None
    rejection_reason = ""


class LeaveBalanceFactory(factory.django.DjangoModelFactory):
    """Factory for LeaveBalance — fresh annual balance for the current year.

    ``quota_days`` defaults to the company statutory minimum; tests that
    exercise exhausted balances set it explicitly to ``Decimal("0")`` or
    similar.
    """

    class Meta:
        model = "attendance.LeaveBalance"

    company = factory.SelfAttribute("employee.company")
    employee = factory.SubFactory(EmployeeFactory)
    leave_type = factory.SubFactory(LeaveTypeFactory)
    year = factory.LazyFunction(date.today().year)
    quota_days = Decimal(str(DEFAULT_ANNUAL_LEAVE_DAYS))
    used_days = Decimal("0")
    carry_over_days = Decimal("0")


class SiteFactory(factory.django.DjangoModelFactory):
    """Factory for Site — Jakarta office with company-default geofence."""

    class Meta:
        model = "attendance.Site"

    company = factory.SubFactory(CompanyFactory)
    name = factory.Sequence(lambda n: f"Site {n}")
    code = factory.Sequence(lambda n: f"SITE{n:04d}")
    latitude = Decimal("-6.200000")
    longitude = Decimal("106.816666")
    geofence_radius_meters = DEFAULT_GEOFENCE_RADIUS_METERS
    status = "active"


class SiteAssignmentFactory(factory.django.DjangoModelFactory):
    """Factory for SiteAssignment — open assignment (effective_until=None)."""

    class Meta:
        model = "attendance.SiteAssignment"

    company = factory.SelfAttribute("employee.company")
    employee = factory.SubFactory(EmployeeFactory)
    site = factory.SubFactory(SiteFactory)
    effective_from = factory.LazyFunction(date.today)
    effective_until = None  # open assignment


class ProjectFactory(factory.django.DjangoModelFactory):
    """Factory for Project — independent of a site by default."""

    class Meta:
        model = "attendance.Project"

    company = factory.SubFactory(CompanyFactory)
    name = factory.Sequence(lambda n: f"Project {n}")
    code = factory.Sequence(lambda n: f"PRJ{n:04d}")
    site = None
    status = "active"


class ProjectAssignmentFactory(factory.django.DjangoModelFactory):
    """Factory for ProjectAssignment — open assignment (effective_until=None)."""

    class Meta:
        model = "attendance.ProjectAssignment"

    company = factory.SelfAttribute("employee.company")
    employee = factory.SubFactory(EmployeeFactory)
    project = factory.SubFactory(ProjectFactory)
    effective_from = factory.LazyFunction(date.today)
    effective_until = None  # open assignment


class AttendanceDisputeFactory(factory.django.DjangoModelFactory):
    """Factory for AttendanceDispute — OPEN dispute raised by the log's owner."""

    class Meta:
        model = "attendance.AttendanceDispute"

    company = factory.SelfAttribute("attendance_log.company")
    attendance_log = factory.SubFactory(AttendanceLogFactory)
    raised_by = factory.SelfAttribute("attendance_log.employee")
    reason = "Clock-in timestamp does not match reality."
    evidence_photo_key = ""
    status = "open"
    resolved_by = None
    resolved_at = None
    resolution_note = ""
