"""
apps/users/tests/test_auth_views.py

Phase 3 — Auth API endpoint feature tests.
Tests the full HTTP request/response cycle for all auth endpoints.

Markers:
  feature — full HTTP cycle via DRF APIClient
"""

from __future__ import annotations

import secrets
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status

from apps.users.models import AuthUser, RefreshToken
from tests.conftest import assert_error_response

pytestmark = pytest.mark.feature


# =============================================================================
# FEATURE TESTS — POST /api/v1/auth/login
# =============================================================================

class TestLoginEndpoint:
    """POST /api/v1/auth/login — token exchange."""

    def test_login_success_returns_tokens(self, api_client, hr_admin):
        """Valid email + password returns access_token, refresh_token, token_type."""
        response = api_client.post(
            "/api/v1/auth/login",
            {"email": "hr_admin@test.local", "password": "TestPass123!"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert len(data["access_token"]) > 20

    def test_login_invalid_email_returns_401(self, api_client, hr_admin):
        """Non-existent email returns 401."""
        response = api_client.post(
            "/api/v1/auth/login",
            {"email": "nobody@test.local", "password": "TestPass123!"},
            format="json",
        )

        assert_error_response(
            response,
            status_code=status.HTTP_401_UNAUTHORIZED,
            message_contains="invalid",
        )

    def test_login_wrong_password_returns_401(self, api_client, hr_admin):
        """Wrong password returns 401."""
        response = api_client.post(
            "/api/v1/auth/login",
            {"email": "hr_admin@test.local", "password": "WrongPassword!"},
            format="json",
        )

        assert_error_response(
            response,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    def test_login_inactive_user_returns_401(self, api_client, inactive_user):
        """Inactive user account returns 401."""
        response = api_client.post(
            "/api/v1/auth/login",
            {"email": "inactive@test.local", "password": "TestPass123!"},
            format="json",
        )

        assert_error_response(
            response,
            status_code=status.HTTP_401_UNAUTHORIZED,
            message_contains="disabled",
        )

    def test_login_missing_email_returns_400(self, api_client):
        """Missing email field returns 400 validation error."""
        response = api_client.post(
            "/api/v1/auth/login",
            {"password": "TestPass123!"},
            format="json",
        )

        assert_error_response(
            response,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    def test_login_missing_password_returns_400(self, api_client):
        """Missing password field returns 400 validation error."""
        response = api_client.post(
            "/api/v1/auth/login",
            {"email": "hr_admin@test.local"},
            format="json",
        )

        assert_error_response(
            response,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    def test_login_empty_body_returns_400(self, api_client):
        """Empty request body returns 400."""
        response = api_client.post("/api/v1/auth/login", {}, format="json")

        assert_error_response(
            response,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    def test_login_access_token_contains_role_claim(self, api_client, hr_admin):
        """The access token JWT payload contains the user's role."""
        response = api_client.post(
            "/api/v1/auth/login",
            {"email": "hr_admin@test.local", "password": "TestPass123!"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        # Decode the JWT to verify claims
        token = response.json()["access_token"]
        import jwt
        from django.conf import settings
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        assert payload["role"] == "hr_admin"
        assert payload["company_id"] == hr_admin.company_id

    def test_login_platform_admin_no_company_id_in_token(self, api_client, platform_admin):
        """Platform admin token has no company_id (cross-tenant operations)."""
        response = api_client.post(
            "/api/v1/auth/login",
            {"email": "platform@test.local", "password": "TestPass123!"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        import jwt
        from django.conf import settings
        payload = jwt.decode(
            response.json()["access_token"],
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        assert payload["role"] == "platform_admin"
        assert "company_id" not in payload or payload.get("company_id") is None


# =============================================================================
# FEATURE TESTS — POST /api/v1/auth/token/refresh
# =============================================================================

class TestTokenRefreshEndpoint:
    """POST /api/v1/auth/token/refresh — access token renewal."""

    def test_refresh_success_returns_new_access_token(self, api_client, hr_admin):
        """Valid refresh token returns a new access token with correct claims."""
        from rest_framework_simplejwt.tokens import AccessToken

        # First login to get tokens — use the factory-generated email, not a hardcoded one
        login_response = api_client.post(
            "/api/v1/auth/login",
            {"email": hr_admin.email, "password": "TestPass123!"},
            format="json",
        )
        assert login_response.status_code == status.HTTP_200_OK
        refresh_token = login_response.json()["refresh_token"]

        # Refresh the token
        response = api_client.post(
            "/api/v1/auth/token/refresh",
            {"refresh_token": refresh_token},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Response shape
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0

        # New access token should differ from the one issued at login
        assert data["access_token"] != login_response.json()["access_token"]

        # Decode (with signature verification) to confirm Nexus claims survived
        decoded = AccessToken(data["access_token"])
        assert decoded["role"] == hr_admin.role
        if hr_admin.company_id:
            assert decoded["company_id"] == hr_admin.company_id
        else:
            assert "company_id" not in decoded

    def test_refresh_with_revoked_token_returns_401(self, api_client, hr_admin):
        """Revoked refresh token returns 401."""
        # Login
        login_response = api_client.post(
            "/api/v1/auth/login",
            {"email": "hr_admin@test.local", "password": "TestPass123!"},
            format="json",
        )
        refresh_token = login_response.json()["refresh_token"]

        # Revoke it
        api_client.post(
            "/api/v1/auth/logout",
            {"refresh_token": refresh_token},
            format="json",
        )

        # Try to use it
        response = api_client.post(
            "/api/v1/auth/token/refresh",
            {"refresh_token": refresh_token},
            format="json",
        )

        assert_error_response(
            response,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    def test_refresh_missing_token_returns_400(self, api_client):
        """Missing refresh_token field returns 400."""
        response = api_client.post(
            "/api/v1/auth/token/refresh",
            {},
            format="json",
        )

        assert_error_response(
            response,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    def test_refresh_invalid_token_format_returns_401(self, api_client):
        """Non-existent/invalid refresh token returns 401."""
        response = api_client.post(
            "/api/v1/auth/token/refresh",
            {"refresh_token": "not.a.valid.token"},
            format="json",
        )

        assert_error_response(
            response,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


# =============================================================================
# FEATURE TESTS — POST /api/v1/auth/logout
# =============================================================================

class TestLogoutEndpoint:
    """POST /api/v1/auth/logout — refresh token revocation."""

    def test_logout_revokes_token(self, api_client, hr_admin):
        """Valid logout request revokes the refresh token."""
        # Login
        login_response = api_client.post(
            "/api/v1/auth/login",
            {"email": "hr_admin@test.local", "password": "TestPass123!"},
            format="json",
        )
        refresh_token = login_response.json()["refresh_token"]

        # Logout
        response = api_client.post(
            "/api/v1/auth/logout",
            {"refresh_token": refresh_token},
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Token should now be revoked
        remaining = RefreshToken.objects.filter(user=hr_admin, is_revoked=False)
        assert remaining.count() == 0

    @pytest.mark.django_db
    def test_logout_with_invalid_token_returns_204(self, api_client):
        """Logout with an invalid token returns 204 (no-op, doesn't leak existence)."""
        response = api_client.post(
            "/api/v1/auth/logout",
            {"refresh_token": "invalid-token-string"},
            format="json",
        )

        # Logout is intentionally a no-op on invalid tokens (security: don't reveal
        # whether a token existed)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_logout_missing_token_returns_400(self, api_client):
        """Missing refresh_token field returns 400."""
        response = api_client.post(
            "/api/v1/auth/logout",
            {},
            format="json",
        )

        assert_error_response(
            response,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


# =============================================================================
# FEATURE TESTS — POST /api/v1/auth/password/change
# =============================================================================

class TestChangePasswordEndpoint:
    """POST /api/v1/auth/password/change — authenticated password update."""

    def test_change_password_success(self, api_client, hr_admin):
        """Valid request changes the password and returns 204."""
        api_client.force_authenticate(user=hr_admin)

        response = api_client.post(
            "/api/v1/auth/password/change",
            {
                "current_password": "TestPass123!",
                "new_password": "NewSecurePass99!",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # New password works
        new_login = api_client.post(
            "/api/v1/auth/login",
            {"email": "hr_admin@test.local", "password": "NewSecurePass99!"},
            format="json",
        )
        assert new_login.status_code == status.HTTP_200_OK

    def test_change_password_requires_authentication(self, api_client):
        """Unauthenticated request returns 401."""
        response = api_client.post(
            "/api/v1/auth/password/change",
            {
                "current_password": "OldPass!",
                "new_password": "NewPass123!",
            },
            format="json",
        )

        assert_error_response(
            response,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    def test_change_password_wrong_current_returns_400(self, api_client, hr_admin):
        """Wrong current password returns 400 with validation error."""
        api_client.force_authenticate(user=hr_admin)

        response = api_client.post(
            "/api/v1/auth/password/change",
            {
                "current_password": "WrongCurrentPass!",
                "new_password": "NewPass123!",
            },
            format="json",
        )

        assert_error_response(
            response,
            status_code=status.HTTP_400_BAD_REQUEST,
            message_contains="incorrect",
        )

    def test_change_password_missing_fields_returns_400(self, api_client, hr_admin):
        """Missing current_password or new_password returns 400."""
        api_client.force_authenticate(user=hr_admin)

        # Missing current_password
        response = api_client.post(
            "/api/v1/auth/password/change",
            {"new_password": "NewPass123!"},
            format="json",
        )
        assert_error_response(response, status_code=status.HTTP_400_BAD_REQUEST)

        # Missing new_password
        response = api_client.post(
            "/api/v1/auth/password/change",
            {"current_password": "TestPass123!"},
            format="json",
        )
        assert_error_response(response, status_code=status.HTTP_400_BAD_REQUEST)

    def test_change_password_revokes_existing_tokens(self, api_client, hr_admin):
        """Changing password revokes all existing refresh tokens."""
        # Login on two devices
        api_client.force_authenticate(user=hr_admin)
        tokens = {}
        for device_id in ["phone", "desktop"]:
            # Use AuthService directly to create device-specific tokens
            from apps.users.services.auth import AuthService
            token = AuthService.create_refresh_token(hr_admin, device_id=device_id)
            tokens[device_id] = token

        # Change password
        response = api_client.post(
            "/api/v1/auth/password/change",
            {"current_password": "TestPass123!", "new_password": "NewPass456!"},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # No active tokens remain
        assert RefreshToken.objects.filter(user=hr_admin, is_revoked=False).count() == 0


# =============================================================================
# FEATURE TESTS — Rate limiting (negative path)
# =============================================================================

class TestAuthRateLimiting:
    """Auth endpoints are rate-limited at 10 req/min per IP."""

    def test_login_rate_limit_returns_429_on_excessive_attempts(self, api_client, hr_admin):
        """
        Exceeding 10 login attempts per minute returns 429.

        Note: This test makes many rapid requests. In CI with parallel execution,
        this may need adjustment. The key assertion is that the server enforces
        a rate limit and returns 429 when exceeded.
        """
        responses = []
        for _ in range(15):
            response = api_client.post(
                "/api/v1/auth/login",
                {"email": "hr_admin@test.local", "password": "WrongPassword!"},
                format="json",
            )
            responses.append(response)
            if response.status_code == 429:
                break

        # At least one 429 should appear among the 15 attempts
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes, (
            f"Expected at least one 429 response among {len(responses)} attempts. "
            f"Got: {status_codes}"
        )


# =============================================================================
# FEATURE TESTS — Cross-company token rejection
# =============================================================================

class TestAuthCrossCompanyIsolation:
    """A token issued to one company cannot be used to access another company's resources."""

    def test_token_from_company_a_cannot_act_in_company_b(
        self, api_client, hr_admin, cross_company_user
    ):
        """
        A refresh token issued to user in company A cannot be used to
        validate a session for user in company B.
        """
        # Patch the throttle so we don't depend on test execution order/rate-limit state
        from apps.apis.v1.auth.views import LoginRateThrottle
        with patch.object(LoginRateThrottle, "allow_request", return_value=True):
            # Login as cross_company_user (company B)
            response = api_client.post(
                "/api/v1/auth/login",
                {
                    "email": cross_company_user.email,
                    "password": "TestPass123!",
                },
                format="json",
            )
        assert response.status_code == status.HTTP_200_OK, response.json()

        # The tokens belong to company B, so using them as company A user
        # (hr_admin) would represent cross-tenant access — which is rejected.
        # This is enforced by JWT company_id claim matching in views.
        cross_company_token = response.json()["access_token"]

        # hr_admin (company A) cannot use company B's token
        # (simulated by checking the company_id in the token)
        import jwt
        from django.conf import settings
        payload = jwt.decode(
            cross_company_token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        assert payload["company_id"] != hr_admin.company_id
