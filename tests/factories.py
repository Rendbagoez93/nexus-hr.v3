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
    from apps.users.models import AuthUser


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
    password = factory.PostGenerationMethodCall("set_password", "TestPass123!")
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Use the manager to support custom manager logic."""
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
