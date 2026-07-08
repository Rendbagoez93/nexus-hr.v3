"""
apps/companies/tests/test_models.py

Phase 2 — Company model tests.
Tests Company, SubscriptionPlan, CompanySubscription constraints and computed properties.

Markers:
  unit — model constraints, __str__, field defaults
  integration — subscription linking, billing period validation
  feature — (no feature tests yet — Company CRUD via Django Admin not tested via API)
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from apps.companies.choices import INDUSTRY_CHOICES, SUBSCRIPTION_TIER_CHOICES
from apps.companies.models import Company, CompanySubscription, SubscriptionPlan

pytestmark = pytest.mark.unit


# =============================================================================
# UNIT TESTS — Company model
# =============================================================================

class TestCompanyModel:
    """Company model constraints, defaults, and __str__."""

    def test_company_str_returns_name(self, company):
        assert str(company) == company.name

    def test_company_defaults(self, db):
        """Company has sensible defaults when only name is provided."""
        c = Company.objects.create(name="Default Corp")
        assert c.industry == "office"
        assert c.subscription_tier == "core"
        assert c.is_active is True
        assert c.geofence_radius_meters == 100
        assert c.emp_number_prefix == "NXS"

    def test_company_geofence_fields(self, company):
        """Company stores geofence configuration for mobile clock-in validation."""
        assert hasattr(company, "geofence_latitude")
        assert hasattr(company, "geofence_longitude")
        assert hasattr(company, "geofence_radius_meters")

    def test_company_emp_number_prefix(self, company):
        """Company has a configurable prefix for employee number generation."""
        assert company.emp_number_prefix is not None
        assert len(company.emp_number_prefix) <= 10

    def test_company_is_active_default(self, db):
        """New companies are active by default."""
        c = Company.objects.create(name="Active Test")
        assert c.is_active is True

    def test_company_soft_delete(self, company):
        """Deactivating a company sets is_active=False and deleted_at."""
        assert company.is_active is True
        assert company.deleted_at is None

        company.deactivate()

        assert company.is_active is False
        assert company.deleted_at is not None

    def test_company_industry_choices(self):
        """Industry choices match the defined choices."""
        valid_industries = [choice[0] for choice in INDUSTRY_CHOICES]
        assert "manufacturing" in valid_industries
        assert "construction" in valid_industries
        assert "mining" in valid_industries
        assert "office" in valid_industries

    def test_company_subscription_tier_choices(self):
        """Subscription tier choices match the defined choices."""
        valid_tiers = [choice[0] for choice in SUBSCRIPTION_TIER_CHOICES]
        assert "core" in valid_tiers
        assert "attendance" in valid_tiers
        assert "hse" in valid_tiers
        assert "payroll" in valid_tiers


# =============================================================================
# UNIT TESTS — SubscriptionPlan model
# =============================================================================

class TestSubscriptionPlanModel:
    """SubscriptionPlan model constraints and __str__."""

    def test_plan_str(self, subscription_plan):
        assert str(subscription_plan) == f"{subscription_plan.name} ({subscription_plan.code})"

    def test_plan_module_flags_default_false(self, db):
        """New plans have all module flags False by default."""
        plan = SubscriptionPlan.objects.create(
            name="Minimal Plan",
            code="minimal",
            price_per_employee_per_month="10000.00",
        )
        assert plan.has_attendance is False
        assert plan.has_hse is False
        assert plan.has_payroll is False
        assert plan.is_active is True

    def test_plan_with_all_modules(self, full_plan):
        """Full plan has all modules enabled."""
        assert full_plan.has_attendance is True
        assert full_plan.has_hse is True
        assert full_plan.has_payroll is True

    def test_plan_code_is_unique(self, subscription_plan, db):
        """Plan code must be unique."""
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            SubscriptionPlan.objects.create(
                name="Duplicate Code Plan",
                code=subscription_plan.code,  # Same code as module-scoped fixture
                price_per_employee_per_month="10000.00",
            )

    def test_plan_name_is_unique(self, subscription_plan, db):
        """Plan name must be unique."""
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            SubscriptionPlan.objects.create(
                name=subscription_plan.name,  # Same name as module-scoped fixture
                code="unique_code",
                price_per_employee_per_month="10000.00",
            )


# =============================================================================
# UNIT TESTS — CompanySubscription model
# =============================================================================

class TestCompanySubscriptionModel:
    """CompanySubscription model linking Company to SubscriptionPlan."""

    def test_subscription_str(self, company_subscription):
        expected = f"{company_subscription.company.name} → {company_subscription.plan.name}"
        assert str(company_subscription) == expected

    def test_subscription_links_company_and_plan(self, company_subscription):
        """CompanySubscription has FKs to both Company and SubscriptionPlan."""
        assert isinstance(company_subscription.company, Company)
        assert isinstance(company_subscription.plan, SubscriptionPlan)

    def test_active_employee_count_default(self, company_subscription):
        """New subscriptions start with 0 active employees."""
        assert company_subscription.active_employee_count == 0

    def test_subscription_billing_period(self, company_subscription):
        """Billing period fields are Date fields (not DateTime)."""
        assert isinstance(company_subscription.billing_period_start, date)
        assert isinstance(company_subscription.billing_period_end, date)

    def test_subscription_ordering(self, company, subscription_plan, full_plan, db):
        """CompanySubscriptions are ordered by billing_period_end descending."""
        today = date.today().replace(day=1)

        # Create two subscriptions with different end dates
        sub1 = CompanySubscription.objects.create(
            company=company,
            plan=subscription_plan,
            billing_period_start=today,
            billing_period_end=today + timedelta(days=180),
            is_active=True,
        )
        sub2 = CompanySubscription.objects.create(
            company=company,
            plan=full_plan,
            billing_period_start=today,
            billing_period_end=today + timedelta(days=365),
            is_active=True,
        )

        subs = list(CompanySubscription.objects.filter(company=company))
        # Most recent (longest-end) first
        assert subs[0] == sub2
        assert subs[1] == sub1

    def test_plan_protection_on_delete(self, subscription_plan, db):
        """Deleting a SubscriptionPlan is protected if linked subscriptions exist."""
        from django.db.models import ProtectedError

        company = Company.objects.create(name="Plan Delete Test", is_active=True)
        CompanySubscription.objects.create(
            company=company,
            plan=subscription_plan,
            billing_period_start=date.today(),
            billing_period_end=date.today() + timedelta(days=365),
        )

        with pytest.raises(ProtectedError):
            subscription_plan.delete()


# =============================================================================
# INTEGRATION TESTS — Subscription & Billing
# =============================================================================

class TestSubscriptionBillingIntegration:
    """Integration tests for subscription billing period and employee counts."""

    @pytest.mark.integration
    def test_subscriptions_reverse_relation(self, company, company_subscription):
        """Company has a subscriptions reverse relation via ForeignKey."""
        assert hasattr(company, "subscriptions")
        assert company.subscriptions.filter(pk=company_subscription.pk).exists()

    @pytest.mark.integration
    def test_multiple_companies_same_plan(self, subscription_plan, db):
        """Multiple companies can share the same SubscriptionPlan."""
        companies = [Company.objects.create(name=f"Multi {i}", is_active=True) for i in range(3)]
        for company in companies:
            CompanySubscription.objects.create(
                company=company,
                plan=subscription_plan,
                billing_period_start=date.today(),
                billing_period_end=date.today() + timedelta(days=365),
            )
        assert subscription_plan.subscriptions.count() == 3

    @pytest.mark.integration
    def test_billing_period_end_must_be_after_start(self, company, subscription_plan, db):
        """Billing period end must be after billing period start."""
        from django.core.exceptions import ValidationError

        sub = CompanySubscription(
            company=company,
            plan=subscription_plan,
            billing_period_start=date.today(),
            billing_period_end=date.today() - timedelta(days=1),  # Before start
        )
        with pytest.raises(ValidationError):
            sub.full_clean()

    @pytest.mark.integration
    def test_active_employee_count_update(self, company_subscription):
        """active_employee_count can be updated without touching FK relations."""
        assert company_subscription.active_employee_count == 0
        company_subscription.active_employee_count = 50
        company_subscription.save()
        company_subscription.refresh_from_db()
        assert company_subscription.active_employee_count == 50


# =============================================================================
# INTEGRATION TESTS — Tenant & Industry
# =============================================================================

class TestCompanyTenantIsolation:
    """Cross-company data isolation."""

    @pytest.mark.integration
    def test_two_companies_have_distinct_prefixes(self, two_companies):
        """Two companies get distinct emp_number_prefix values."""
        alpha, beta = two_companies
        assert alpha.emp_number_prefix != beta.emp_number_prefix

    @pytest.mark.integration
    def test_company_active_filter_excludes_inactive(self, company, inactive_company, db):
        """Querying with is_active=True excludes soft-deleted companies."""
        active = Company.objects.filter(is_active=True)
        assert active.filter(pk=company.pk).exists()
        assert not active.filter(pk=inactive_company.pk).exists()
