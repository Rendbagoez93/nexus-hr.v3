"""
apps/companies/tests/conftest.py — Fixtures for companies tests.

Scope strategy:
  session    — (none needed yet)
  function   — All fixtures (SubscriptionPlan, Company, CompanySubscription per-test instances)
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

# ---------------------------------------------------------------------------
# Function-scoped SubscriptionPlan fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def subscription_plan(db):
    """Function-scoped SubscriptionPlan for test isolation."""
    from apps.companies.models import SubscriptionPlan
    return SubscriptionPlan.objects.create(
        name="Test Core Plan",
        code="test_core",
        has_attendance=False,
        has_hse=False,
        has_payroll=False,
        price_per_employee_per_month="50000.00",
        is_active=True,
    )


@pytest.fixture
def attendance_plan(db):
    """Function-scoped SubscriptionPlan with attendance module enabled."""
    from apps.companies.models import SubscriptionPlan
    return SubscriptionPlan.objects.create(
        name="Test Attendance Plan",
        code="test_attendance",
        has_attendance=True,
        has_hse=False,
        has_payroll=False,
        price_per_employee_per_month="75000.00",
        is_active=True,
    )


@pytest.fixture
def hse_plan(db):
    """Function-scoped SubscriptionPlan with HSE module enabled."""
    from apps.companies.models import SubscriptionPlan
    return SubscriptionPlan.objects.create(
        name="Test HSE Plan",
        code="test_hse",
        has_attendance=False,
        has_hse=True,
        has_payroll=False,
        price_per_employee_per_month="75000.00",
        is_active=True,
    )


@pytest.fixture
def full_plan(db):
    """Function-scoped SubscriptionPlan with all modules enabled."""
    from apps.companies.models import SubscriptionPlan
    return SubscriptionPlan.objects.create(
        name="Test Full Plan",
        code="test_full",
        has_attendance=True,
        has_hse=True,
        has_payroll=True,
        price_per_employee_per_month="150000.00",
        is_active=True,
    )


# ---------------------------------------------------------------------------
# Function-scoped instances
# ---------------------------------------------------------------------------

@pytest.fixture
def company(db):
    """A single active Company instance."""
    from apps.companies.models import Company
    return Company.objects.create(
        name="Nexus Test Corp",
        industry="manufacturing",
        subscription_tier="core",
        is_active=True,
        emp_number_prefix="NXT",
        geofence_radius_meters=100,
    )


@pytest.fixture
def inactive_company(db):
    """A soft-deleted Company instance."""
    from apps.companies.models import Company
    return Company.objects.create(
        name="Inactive Corp",
        industry="office",
        subscription_tier="core",
        is_active=False,
    )


@pytest.fixture
def two_companies(db):
    """Two distinct active Company instances."""
    from apps.companies.models import Company
    alpha = Company.objects.create(
        name="Company Alpha",
        industry="manufacturing",
        subscription_tier="core",
        is_active=True,
        emp_number_prefix="ALP",
    )
    beta = Company.objects.create(
        name="Company Beta",
        industry="construction",
        subscription_tier="payroll",
        is_active=True,
        emp_number_prefix="BTX",
    )
    return alpha, beta


@pytest.fixture
def company_subscription(company, subscription_plan):
    """CompanySubscription linking company to core plan."""
    from apps.companies.models import CompanySubscription
    return CompanySubscription.objects.create(
        company=company,
        plan=subscription_plan,
        billing_period_start=date.today().replace(day=1),
        billing_period_end=(date.today().replace(day=1) + timedelta(days=365)).replace(month=1),
        active_employee_count=0,
        is_active=True,
    )


@pytest.fixture
def attendance_subscription(company, attendance_plan):
    """CompanySubscription with attendance module enabled."""
    from apps.companies.models import CompanySubscription
    return CompanySubscription.objects.create(
        company=company,
        plan=attendance_plan,
        billing_period_start=date.today().replace(day=1),
        billing_period_end=(date.today().replace(day=1) + timedelta(days=365)).replace(month=1),
        active_employee_count=0,
        is_active=True,
    )
