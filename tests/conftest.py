"""
tests/conftest.py — Shared test fixtures for the entire Nexus HR suite.

Scope strategy:
  session   — Django settings, test DB connection (expensive, read-only)
  module    — Company, SubscriptionPlan reference data (reused across a test file)
  class     — One company + role fixtures per permission-test class
  function  — Everything a test creates, mutates, or asserts on

All fixtures are self-contained. Tests should use factory-boy factories defined
in tests/factories.py, not Model.objects.create() directly.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import TYPE_CHECKING, Generator

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

if TYPE_CHECKING:
    from apps.companies.models import Company, CompanySubscription, SubscriptionPlan
    from apps.users.models import AuthUser

# ---------------------------------------------------------------------------
# Django settings bootstrap — must happen before any Django ORM import
# ---------------------------------------------------------------------------

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")


# ---------------------------------------------------------------------------
# Django pytest-django hooks
# ---------------------------------------------------------------------------

def pytest_configure() -> None:
    import django
    django.setup()


# ---------------------------------------------------------------------------
# APIClient fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client() -> APIClient:
    """Unauthenticated DRF API client."""
    return APIClient()


# ---------------------------------------------------------------------------
# User fixtures — bare AuthUser objects (for login tests that use email+password)
# ---------------------------------------------------------------------------

@pytest.fixture
def hr_admin():
    """HR Admin user — use for login tests that POST email+password."""
    from tests.factories import HRAdminFactory
    return HRAdminFactory()


@pytest.fixture
def inactive_user():
    """Inactive user — for auth negative-path tests."""
    from tests.factories import InactiveUserFactory
    return InactiveUserFactory()


@pytest.fixture
def platform_admin():
    """Platform admin user (superuser, no company)."""
    from tests.factories import PlatformAdminFactory
    return PlatformAdminFactory()


@pytest.fixture
def cross_company_user():
    """Second-company HR Admin — for cross-tenant isolation tests."""
    from tests.factories import HRAdminFactory
    return HRAdminFactory()


# ---------------------------------------------------------------------------
# DRF authenticated API clients
# ---------------------------------------------------------------------------

@pytest.fixture
def platform_admin_client(api_client: APIClient) -> APIClient:
    """
    APIClient authenticated as a platform admin (is_superuser=True, no company).
    """
    from tests.factories import PlatformAdminFactory
    user = PlatformAdminFactory()
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def hr_admin_client(api_client: APIClient) -> APIClient:
    """
    APIClient authenticated as an HR Admin within a company.
    """
    from tests.factories import HRAdminFactory
    user = HRAdminFactory()
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def manager_client(api_client: APIClient) -> APIClient:
    """
    APIClient authenticated as a Manager within a company.
    """
    from tests.factories import ManagerFactory
    user = ManagerFactory()
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def employee_client(api_client: APIClient) -> APIClient:
    """
    APIClient authenticated as a plain Employee within a company.
    """
    from tests.factories import EmployeeUserFactory
    user = EmployeeUserFactory()
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def hse_officer_client(api_client: APIClient) -> APIClient:
    """
    APIClient authenticated as an HSE Officer within a company.
    """
    from tests.factories import HSEOfficerFactory
    user = HSEOfficerFactory()
    api_client.force_authenticate(user=user)
    return api_client


# ---------------------------------------------------------------------------
# Second-company clients (for cross-tenant isolation tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def other_company_client(api_client: APIClient) -> APIClient:
    """APIClient authenticated as an HR Admin in a second company."""
    from tests.factories import HRAdminFactory
    user = HRAdminFactory()  # Each factory call creates a new company
    api_client.force_authenticate(user=user)
    return api_client


# ---------------------------------------------------------------------------
# Helper: assert helper functions for consistent error responses
# ---------------------------------------------------------------------------

def assert_error_response(
    response,
    *,
    status_code: int,
    error_code: str | None = None,
    message_contains: str | None = None,
) -> None:
    """
    Assert a DRF response has the expected error shape.

    Uses the standardized Nexus error envelope:
      { "error": "...", "message": "...", "status": N, "details": {...} }
    or a simple DRF { "detail": "..." } response.
    """
    assert response.status_code == status_code, (
        f"Expected status {status_code}, got {response.status_code}. "
        f"Response: {response.json()}"
    )
    data = response.json()

    # Simple DRF error shape
    if "detail" in data:
        if message_contains:
            assert message_contains.lower() in str(data["detail"]).lower()
        return

    # Nexus standardized error envelope
    if "error" in data:
        if error_code:
            assert data["error"] == error_code, (
                f"Expected error code '{error_code}', got '{data['error']}'"
            )
    if "message" in data and message_contains:
        assert message_contains.lower() in str(data["message"]).lower(), (
            f"Expected message to contain '{message_contains}', got '{data['message']}'"
        )


def assert_cross_tenant_forbidden(response) -> None:
    """
    Assert that accessing a cross-company resource returns 403, NOT 404.

    This is a deliberate security rule — leaking 404 means an attacker can
    enumerate valid resource IDs. Always use this instead of assert 404 when
    testing cross-tenant access.
    """
    assert response.status_code == 403, (
        f"Cross-tenant access must return 403, got {response.status_code}. "
        f"Response: {response.json()}"
    )
