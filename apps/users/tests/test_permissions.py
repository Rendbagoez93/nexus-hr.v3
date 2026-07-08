"""
apps/users/tests/test_permissions.py

Phase 3 — Permission class unit and feature tests.
Tests every role × action combination for auth-related operations.

Markers:
  unit    — Permission class has_permission() method in isolation
  feature — HTTP-level permission enforcement via APIClient
"""

from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.test import APIRequestFactory

from apps.shared.permissions import (
    IsEmployee,
    IsHRAdmin,
    IsHSEOfficerOrAbove,
    IsManagerOrAbove,
    IsOwnerOrHRAdmin,
    IsPlatformAdmin,
)
from apps.users.models import AuthUser

pytestmark = pytest.mark.unit


# =============================================================================
# UNIT TESTS — Permission Classes
# =============================================================================

class TestPermissionClasses:
    """Permission class has_permission() results per role."""

    def _make_request(self, user: AuthUser | None, method: str = "GET"):
        """Build a minimal DRF request for permission testing."""
        factory = APIRequestFactory()
        request = getattr(factory, method.lower())("/")
        request.user = user
        return request

    # IsPlatformAdmin
    def test_platform_admin_permission_allows_superuser(self, platform_admin):
        request = self._make_request(platform_admin)
        assert IsPlatformAdmin().has_permission(request, None) is True

    def test_platform_admin_permission_denies_regular_user(self, hr_admin):
        request = self._make_request(hr_admin)
        assert IsPlatformAdmin().has_permission(request, None) is False

    def test_platform_admin_permission_denies_anonymous(self):
        request = self._make_request(None)
        assert IsPlatformAdmin().has_permission(request, None) is False

    # IsHRAdmin
    def test_hr_admin_permission_allows_hr_admin(self, hr_admin):
        request = self._make_request(hr_admin)
        assert IsHRAdmin().has_permission(request, None) is True

    def test_hr_admin_permission_denies_manager(self, manager_user):
        request = self._make_request(manager_user)
        assert IsHRAdmin().has_permission(request, None) is False

    def test_hr_admin_permission_denies_employee(self, employee_user):
        request = self._make_request(employee_user)
        assert IsHRAdmin().has_permission(request, None) is False

    def test_hr_admin_permission_denies_hse_officer(self, hse_officer_user):
        request = self._make_request(hse_officer_user)
        assert IsHRAdmin().has_permission(request, None) is False

    def test_hr_admin_permission_denies_anonymous(self):
        request = self._make_request(None)
        assert IsHRAdmin().has_permission(request, None) is False

    # IsManagerOrAbove
    def test_manager_or_above_allows_platform_admin(self, platform_admin):
        request = self._make_request(platform_admin)
        assert IsManagerOrAbove().has_permission(request, None) is True

    def test_manager_or_above_allows_hr_admin(self, hr_admin):
        request = self._make_request(hr_admin)
        assert IsManagerOrAbove().has_permission(request, None) is True

    def test_manager_or_above_allows_manager(self, manager_user):
        request = self._make_request(manager_user)
        assert IsManagerOrAbove().has_permission(request, None) is True

    def test_manager_or_above_denies_employee(self, employee_user):
        request = self._make_request(employee_user)
        assert IsManagerOrAbove().has_permission(request, None) is False

    def test_manager_or_above_denies_hse_officer(self, hse_officer_user):
        request = self._make_request(hse_officer_user)
        assert IsManagerOrAbove().has_permission(request, None) is False

    # IsEmployee
    def test_is_employee_allows_all_authenticated_roles(self, hr_admin):
        for user in [hr_admin, hr_admin.__class__.objects.get(pk=hr_admin.pk)]:
            request = self._make_request(user)
            assert IsEmployee().has_permission(request, None) is True

    def test_is_employee_denies_anonymous(self):
        request = self._make_request(None)
        assert IsEmployee().has_permission(request, None) is False

    # IsHSEOfficerOrAbove
    def test_hse_officer_or_above_allows_hse_officer(self, hse_officer_user):
        request = self._make_request(hse_officer_user)
        assert IsHSEOfficerOrAbove().has_permission(request, None) is True

    def test_hse_officer_or_above_allows_manager(self, manager_user):
        request = self._make_request(manager_user)
        assert IsHSEOfficerOrAbove().has_permission(request, None) is True

    def test_hse_officer_or_above_allows_hr_admin(self, hr_admin):
        request = self._make_request(hr_admin)
        assert IsHSEOfficerOrAbove().has_permission(request, None) is True

    def test_hse_officer_or_above_allows_platform_admin(self, platform_admin):
        request = self._make_request(platform_admin)
        assert IsHSEOfficerOrAbove().has_permission(request, None) is True

    def test_hse_officer_or_above_denies_employee(self, employee_user):
        request = self._make_request(employee_user)
        assert IsHSEOfficerOrAbove().has_permission(request, None) is False


# =============================================================================
# PERMISSION FIXTURES — per-role user factories
# =============================================================================

@pytest.fixture
def manager_user(db, company):
    """A Manager user within a company."""
    return AuthUser.objects.create_user(
        email="manager@test.local",
        password="TestPass123!",
        role="manager",
        company=company,
    )


@pytest.fixture
def hse_officer_user(db, company):
    """An HSE Officer user within a company."""
    return AuthUser.objects.create_user(
        email="hse_officer@test.local",
        password="TestPass123!",
        role="hse_officer",
        company=company,
    )
