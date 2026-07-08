"""
apps/users/tests/conftest.py — Fixtures for users/auth tests.

Scope strategy:
  module     — Shared reference users within a single test file (read-only)
  function   — Per-test users (login, token revocation mutate state)
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    """Unauthenticated DRF API client for feature tests."""
    return APIClient()


@pytest.fixture
def company(db):
    """A shared active company for auth tests.

    Function-scoped to avoid IntegrityError with module-scoped SubscriptionPlan.
    """
    from apps.companies.models import Company
    return Company.objects.create(
        name="Auth Test Corp",
        industry="manufacturing",
        subscription_tier="core",
        is_active=True,
    )


@pytest.fixture
def hr_admin(db, company):
    """An HR Admin user within a company."""
    from apps.users.models import AuthUser
    return AuthUser.objects.create_user(
        email="hr_admin@test.local",
        password="TestPass123!",
        role="hr_admin",
        company=company,
    )


@pytest.fixture
def employee_user(db, company):
    """A plain Employee user within a company."""
    from apps.users.models import AuthUser
    return AuthUser.objects.create_user(
        email="employee@test.local",
        password="TestPass123!",
        role="employee",
        company=company,
    )


@pytest.fixture
def inactive_user(db, company):
    """An inactive AuthUser (is_active=False)."""
    from apps.users.models import AuthUser
    user = AuthUser.objects.create_user(
        email="inactive@test.local",
        password="TestPass123!",
        role="employee",
        company=company,
    )
    user.is_active = False
    user.save()
    return user


@pytest.fixture
def platform_admin(db):
    """A platform admin (no company, is_superuser=True)."""
    from apps.users.models import AuthUser
    return AuthUser.objects.create_superuser(
        email="platform@test.local",
        password="TestPass123!",
    )


@pytest.fixture
def second_company(db):
    """A second distinct company for cross-tenant isolation tests."""
    from apps.companies.models import Company
    return Company.objects.create(
        name="Second Corp",
        industry="construction",
        subscription_tier="core",
        is_active=True,
    )


@pytest.fixture
def cross_company_user(db, second_company):
    """An HR Admin user belonging to a different company."""
    from apps.users.models import AuthUser
    return AuthUser.objects.create_user(
        email="other_company@test.local",
        password="TestPass123!",
        role="hr_admin",
        company=second_company,
    )


@pytest.fixture
def manager_user(db, company):
    """A Manager user within a company."""
    from apps.users.models import AuthUser
    return AuthUser.objects.create_user(
        email="manager@test.local",
        password="TestPass123!",
        role="manager",
        company=company,
    )


@pytest.fixture
def hse_officer_user(db, company):
    """An HSE Officer user within a company."""
    from apps.users.models import AuthUser
    return AuthUser.objects.create_user(
        email="hse_officer@test.local",
        password="TestPass123!",
        role="hse_officer",
        company=company,
    )
