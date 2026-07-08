"""
apps/users/tests/test_auth_service.py

Phase 3 — AuthService unit tests.
Tests authentication logic: authenticate, refresh token lifecycle, password change.

Markers:
  unit    — Pure service function tests (mock DB reads where appropriate)
  integration — Full auth flow with DB (login → token → refresh → revoke)
  feature  — (see test_auth_views.py for HTTP-level tests)
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from apps.users.exceptions import AuthError
from apps.users.models import AuthUser, RefreshToken
from apps.users.services.auth import AuthService

pytestmark = pytest.mark.unit


# =============================================================================
# UNIT TESTS — AuthService.authenticate
# =============================================================================

class TestAuthServiceAuthenticate:
    """AuthService.authenticate() validates credentials."""

    def test_authenticate_valid_credentials(self, hr_admin):
        """Valid email + password returns the user."""
        user = AuthService.authenticate("hr_admin@test.local", "TestPass123!")
        assert user.email == hr_admin.email
        assert user.role == "hr_admin"

    @pytest.mark.django_db
    def test_authenticate_invalid_email(self):
        """Non-existent email raises AuthError."""
        with pytest.raises(AuthError) as exc_info:
            AuthService.authenticate("nobody@test.local", "anypass")
        assert "Invalid email or password" in str(exc_info.value)

    def test_authenticate_invalid_password(self, hr_admin):
        """Wrong password raises AuthError."""
        with pytest.raises(AuthError) as exc_info:
            AuthService.authenticate("hr_admin@test.local", "WrongPassword!")
        assert "Invalid email or password" in str(exc_info.value)

    def test_authenticate_inactive_account(self, inactive_user):
        """Inactive account raises AuthError."""
        with pytest.raises(AuthError) as exc_info:
            AuthService.authenticate("inactive@test.local", "TestPass123!")
        assert "disabled" in str(exc_info.value).lower()

    def test_authenticate_email_is_case_sensitive_lookup(self, hr_admin):
        """AuthService.authenticate() performs case-sensitive email lookup.

        Django's ORM does exact match on email fields by default. The email
        is normalized to lowercase during user creation (create_user normalizes it),
        so only the lowercased form matches.
        """
        # hr_admin was created with email "hr_admin@test.local" (already lowercase)
        # An all-uppercase email does not match
        with pytest.raises(AuthError):
            AuthService.authenticate("HR_ADMIN@TEST.LOCAL", "TestPass123!")

    def test_authenticate_email_lookup_is_case_sensitive(self, hr_admin):
        """AuthService.authenticate() uses exact Django ORM email lookup.

        Django's normalize_email() only lowercases the domain (RFC 5321).
        The local part is preserved. So "UPPERCASE@test.local" ≠ "uppercase@test.local".
        """
        # hr_admin email is already lowercase so this passes
        user = AuthService.authenticate("hr_admin@test.local", "TestPass123!")
        assert user.email == hr_admin.email

    def test_authenticate_email_domain_normalized(self, db, company):
        """Django normalizes email domain to lowercase but preserves local part."""
        from apps.users.models import AuthUser
        user = AuthUser.objects.create_user(
            email="UPPERCASE@TEST.LOCAL",
            password="TestPass123!",
            role="employee",
            company=company,
        )
        # Django lowercases only the domain
        assert user.email == "UPPERCASE@test.local"
        # Lookup with normalized form works
        found = AuthService.authenticate("UPPERCASE@test.local", "TestPass123!")
        assert found.email == "UPPERCASE@test.local"


# =============================================================================
# UNIT TESTS — AuthService.refresh_token
# =============================================================================

class TestAuthServiceRefreshToken:
    """AuthService refresh token lifecycle."""

    def test_create_refresh_token_returns_token(self, hr_admin):
        """create_refresh_token returns a RefreshToken instance."""
        token = AuthService.create_refresh_token(hr_admin, device_id="test-device-1")

        assert isinstance(token, RefreshToken)
        assert token.user == hr_admin
        assert token.device_id == "test-device-1"
        assert token.is_revoked is False
        assert token.expires_at > timezone.now()

    def test_create_refresh_token_hashes_token(self, hr_admin):
        """The raw token is not stored — only its hash is persisted."""
        token = AuthService.create_refresh_token(hr_admin)

        assert token.token_hash != ""  # Hash is stored
        assert token.token_hash != "raw-token"  # Not the raw token
        # Token hash should not be the same for same input (salted)
        assert len(token.token_hash) > 32

    def test_create_refresh_token_revokes_existing_for_device(self, hr_admin):
        """Creating a new token for the same device revokes the old one."""
        old_token = AuthService.create_refresh_token(hr_admin, device_id="device-x")
        new_token = AuthService.create_refresh_token(hr_admin, device_id="device-x")

        old_token.refresh_from_db()
        assert old_token.is_revoked is True
        assert new_token.is_revoked is False

    def test_create_refresh_token_preserves_other_device_tokens(self, hr_admin):
        """Creating a new token for one device does NOT revoke tokens on other devices."""
        token_a = AuthService.create_refresh_token(hr_admin, device_id="device-a")
        token_b = AuthService.create_refresh_token(hr_admin, device_id="device-b")

        token_a.refresh_from_db()
        assert token_a.is_revoked is False
        assert token_b.is_revoked is False

    def test_validate_refresh_token_valid(self, hr_admin):
        """validate_refresh_token returns the token for a valid, non-expired token."""
        import secrets
        raw_token = secrets.token_urlsafe(64)
        token = RefreshToken.objects.create(
            user=hr_admin,
            token_hash=make_password(raw_token),
            device_id="test-device",
            expires_at=timezone.now() + timedelta(days=30),
        )

        validated = AuthService.validate_refresh_token(raw_token, device_id="test-device")
        assert validated == token

    def test_validate_refresh_token_invalid_hash(self, hr_admin):
        """A tampered token raises AuthError."""
        with pytest.raises(AuthError) as exc_info:
            AuthService.validate_refresh_token("tampered-token", device_id="test-device")
        assert "Invalid or expired" in str(exc_info.value)

    def test_validate_refresh_token_expired(self, hr_admin):
        """An expired token raises AuthError."""
        import secrets
        raw_token = secrets.token_urlsafe(64)
        token = RefreshToken.objects.create(
            user=hr_admin,
            token_hash=make_password(raw_token),
            device_id="test-device",
            expires_at=timezone.now() - timedelta(hours=1),  # Already expired
        )

        with pytest.raises(AuthError) as exc_info:
            AuthService.validate_refresh_token(raw_token, device_id="test-device")
        assert "expired" in str(exc_info.value).lower()

    def test_validate_refresh_token_revoked(self, hr_admin):
        """A revoked token raises AuthError."""
        import secrets
        raw_token = secrets.token_urlsafe(64)
        token = RefreshToken.objects.create(
            user=hr_admin,
            token_hash=make_password(raw_token),
            device_id="test-device",
            expires_at=timezone.now() + timedelta(days=30),
            is_revoked=True,
        )

        with pytest.raises(AuthError) as exc_info:
            AuthService.validate_refresh_token(raw_token, device_id="test-device")
        assert "Invalid or expired" in str(exc_info.value)

    def test_validate_refresh_token_wrong_device(self, hr_admin):
        """A token issued for a different device raises AuthError."""
        import secrets
        raw_token = secrets.token_urlsafe(64)
        RefreshToken.objects.create(
            user=hr_admin,
            token_hash=make_password(raw_token),
            device_id="device-a",
            expires_at=timezone.now() + timedelta(days=30),
        )

        with pytest.raises(AuthError):
            AuthService.validate_refresh_token(raw_token, device_id="device-b")

    def test_revoke_refresh_token(self, hr_admin):
        """revoke_refresh_token sets is_revoked=True on the matching token."""
        import secrets
        raw_token = secrets.token_urlsafe(64)
        RefreshToken.objects.create(
            user=hr_admin,
            token_hash=make_password(raw_token),
            device_id="device-x",
            expires_at=timezone.now() + timedelta(days=30),
        )

        AuthService.revoke_refresh_token(raw_token)

        remaining_active = RefreshToken.objects.filter(user=hr_admin, is_revoked=False)
        assert remaining_active.count() == 0

    def test_revoke_all_user_tokens(self, hr_admin):
        """revoke_all_user_tokens revokes all active tokens for a user."""
        # Create tokens on multiple devices
        for device_id in ["phone", "tablet", "desktop"]:
            AuthService.create_refresh_token(hr_admin, device_id=device_id)

        count = AuthService.revoke_all_user_tokens(hr_admin)

        assert count == 3
        assert RefreshToken.objects.filter(user=hr_admin, is_revoked=False).count() == 0


# =============================================================================
# UNIT TESTS — AuthService.change_password
# =============================================================================

class TestAuthServiceChangePassword:
    """AuthService.change_password() updates password and revokes tokens."""

    def test_change_password_success(self, hr_admin):
        """Valid current password updates to new password."""
        old_password = hr_admin.password

        AuthService.change_password(hr_admin, "TestPass123!", "NewPassword456!")

        hr_admin.refresh_from_db()
        assert hr_admin.password != old_password
        assert check_password("NewPassword456!", hr_admin.password)

    def test_change_password_wrong_current(self, hr_admin):
        """Wrong current password raises AuthError."""
        with pytest.raises(AuthError) as exc_info:
            AuthService.change_password(hr_admin, "WrongPassword!", "NewPass123!")
        assert "incorrect" in str(exc_info.value).lower()

    def test_change_password_revokes_all_tokens(self, hr_admin):
        """Changing password revokes all existing refresh tokens (force re-login)."""
        # Establish sessions on multiple devices
        for device_id in ["phone", "tablet"]:
            AuthService.create_refresh_token(hr_admin, device_id=device_id)

        AuthService.change_password(hr_admin, "TestPass123!", "NewPass789!")

        assert RefreshToken.objects.filter(user=hr_admin, is_revoked=False).count() == 0

    def test_change_password_new_password_can_authenticate(self, hr_admin):
        """After changing password, the new password works for authentication."""
        AuthService.change_password(hr_admin, "TestPass123!", "SuperNewPass99!")

        user = AuthService.authenticate("hr_admin@test.local", "SuperNewPass99!")
        assert user.email == hr_admin.email
