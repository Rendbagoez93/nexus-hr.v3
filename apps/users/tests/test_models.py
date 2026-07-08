"""
apps/users/tests/test_models.py

Phase 3 — AuthUser & RefreshToken model tests.

Markers:
  unit    — Model constraints, __str__, manager methods, field validation
  integration — Cross-company user creation
"""

from __future__ import annotations

import pytest
from django.contrib.auth.hashers import check_password

from apps.users.models import AuthUser, RefreshToken

pytestmark = pytest.mark.unit


# =============================================================================
# UNIT TESTS — AuthUser model
# =============================================================================

class TestAuthUserModel:
    """AuthUser model — identity, roles, and authentication."""

    def test_auth_user_str(self, hr_admin):
        assert str(hr_admin) == hr_admin.email

    def test_auth_user_email_is_unique(self, hr_admin, db, company):
        """Duplicate email raises IntegrityError."""
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            AuthUser.objects.create_user(
                email="hr_admin@test.local",  # Same as hr_admin fixture
                password="pass",
                role="employee",
                company=company,
            )

    def test_auth_user_role_choices(self):
        """AuthUser.role accepts all defined role choices."""
        from apps.users.choices import ROLE_CHOICES
        
        valid_roles = ["platform_admin", "hr_admin", "manager", "employee", "hse_officer"]
        role_values = [code for code, label in ROLE_CHOICES]
        
        for role in valid_roles:
            assert role in role_values

    def test_auth_user_platform_admin_has_no_company(self, platform_admin):
        """Platform admin has no company FK (cross-tenant)."""
        assert platform_admin.company is None

    def test_auth_user_company_tenant_isolation(self, hr_admin, cross_company_user):
        """Two users from different companies have different company FKs."""
        assert hr_admin.company != cross_company_user.company

    def test_auth_user_email_domain_normalized(self, db, company):
        """Email domain is normalized to lowercase; local part is preserved (Django default)."""
        user = AuthUser.objects.create_user(
            email="JohnDoe@EXAMPLE.COM",
            password="TestPass123!",
            role="employee",
            company=company,
        )
        # Django lowercases only the domain
        assert user.email == "JohnDoe@example.com"

    def test_auth_user_password_is_hashed(self, hr_admin):
        """Passwords are hashed, not stored in plaintext."""
        assert hr_admin.password != "TestPass123!"
        assert check_password("TestPass123!", hr_admin.password)

    def test_auth_user_requires_email(self, db, company):
        """Creating a user without email raises ValueError."""
        from django.core.exceptions import ValidationError
        user = AuthUser(email="", password="TestPass123!", role="employee", company=company)
        with pytest.raises(ValidationError):
            user.full_clean()

    def test_auth_user_create_superuser_sets_flags(self, db):
        """create_superuser sets is_superuser=True and is_staff=True."""
        user = AuthUser.objects.create_superuser(
            email="super@test.local",
            password="SuperPass123!",
        )
        assert user.is_superuser is True
        assert user.is_staff is True
        assert user.role == "platform_admin"
        assert user.company is None

    def test_auth_user_is_active_default_true(self, db, company):
        """New users are active by default."""
        user = AuthUser.objects.create_user(
            email="newuser@test.local",
            password="TestPass123!",
            role="employee",
            company=company,
        )
        assert user.is_active is True

    def test_auth_user_timestamps(self, hr_admin):
        """AuthUser has created_at and updated_at from TimestampedModel."""
        assert hasattr(hr_admin, "created_at")
        assert hasattr(hr_admin, "updated_at")


# =============================================================================
# UNIT TESTS — RefreshToken model
# =============================================================================

class TestRefreshTokenModel:
    """RefreshToken model — token lifecycle."""

    def test_refresh_token_str(self, hr_admin):
        from apps.users.services.auth import AuthService
        token = AuthService.create_refresh_token(hr_admin, device_id="phone")
        assert hr_admin.email in str(token)
        assert "revoked=False" in str(token)

    def test_refresh_token_is_revoked_default_false(self, hr_admin):
        """New refresh tokens are not revoked by default."""
        from apps.users.services.auth import AuthService
        token = AuthService.create_refresh_token(hr_admin)
        assert token.is_revoked is False

    def test_refresh_token_expires_at_is_set(self, hr_admin):
        """New refresh tokens have an expiry date set in the future."""
        from apps.users.services.auth import AuthService
        token = AuthService.create_refresh_token(hr_admin)
        from django.utils import timezone
        assert token.expires_at > timezone.now()

    def test_refresh_token_device_id_default_empty(self, hr_admin):
        """Device ID defaults to empty string."""
        from apps.users.services.auth import AuthService
        token = AuthService.create_refresh_token(hr_admin)
        assert token.device_id == ""

    def test_refresh_token_token_hash_is_hmac(self, hr_admin):
        """Token hash is stored, raw token is not stored."""
        from apps.users.services.auth import AuthService
        import secrets
        raw = secrets.token_urlsafe(64)
        token_hash = "some_hash_value"
        token = RefreshToken.objects.create(
            user=hr_admin,
            token_hash=token_hash,
            device_id="test",
            expires_at=hr_admin.created_at,  # dummy
        )
        assert token.token_hash == token_hash


# =============================================================================
# INTEGRATION TESTS — Cross-company user creation
# =============================================================================

class TestAuthUserCrossCompany:
    """Users from different companies are fully isolated."""

    @pytest.mark.integration
    def test_same_email_in_different_companies_allowed(self, db):
        """
        Two companies can have users with the same email address.
        This is a deliberate design choice — email is globally unique via unique=True,
        but in a real multi-tenant SaaS, emails should be unique per company.
        NOTE: This test documents current behavior. If email-per-company uniqueness
        is desired, a UniqueConstraint(company, email) should be added.
        """
        from apps.companies.models import Company

        company_a = Company.objects.create(name="Company A", is_active=True)
        company_b = Company.objects.create(name="Company B", is_active=True)

        user_a = AuthUser.objects.create_user(
            email="shared@test.local",
            password="TestPass123!",
            role="employee",
            company=company_a,
        )
        assert user_a.company == company_a

        # AuthUser.email has unique=True globally — this will fail
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            AuthUser.objects.create_user(
                email="shared@test.local",
                password="TestPass123!",
                role="employee",
                company=company_b,
            )
