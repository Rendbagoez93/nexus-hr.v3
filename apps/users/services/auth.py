"""
apps/users/services/auth.py

Authentication business logic — login, logout, token refresh, password change.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from apps.users.models import AuthUser, RefreshToken


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_at: str


from apps.users.exceptions import AuthError


class AuthService:
    """Handles authentication operations for AuthUser."""

    @staticmethod
    def authenticate(email: str, password: str) -> AuthUser:
        """
        Validate email + password credentials.

        Raises AuthError on failure.
        """
        try:
            user = AuthUser.objects.get(email=email)
        except AuthUser.DoesNotExist:
            raise AuthError("Invalid email or password.")

        if not user.is_active:
            raise AuthError("Account is disabled.")

        if not check_password(password, user.password):
            raise AuthError("Invalid email or password.")

        return user

    @staticmethod
    @transaction.atomic
    def create_refresh_token(user: AuthUser, device_id: str = "") -> RefreshToken:
        """
        Issue a new refresh token for a user.

        Old tokens for the same device are revoked (one active token per device).
        """
        # Revoke existing tokens for this device
        RefreshToken.objects.filter(
            user=user,
            device_id=device_id,
            is_revoked=False,
        ).update(is_revoked=True)

        token = secrets.token_urlsafe(64)
        token_hash = make_password(token)

        return RefreshToken.objects.create(
            user=user,
            token_hash=token_hash,
            device_id=device_id,
            expires_at=timezone.now() + timezone.timedelta(days=30),
        )

    @staticmethod
    def validate_refresh_token(token: str, device_id: str = "") -> RefreshToken:
        """
        Validate a refresh token.

        Raises AuthError on invalid, expired, or revoked token.
        """
        valid_token = None
        for rt in RefreshToken.objects.filter(device_id=device_id, is_revoked=False).select_for_update():
            if check_password(token, rt.token_hash):
                valid_token = rt
                break

        if valid_token is None:
            raise AuthError("Invalid or expired refresh token.")

        if valid_token.expires_at < timezone.now():
            raise AuthError("Refresh token has expired.")

        return valid_token

    @staticmethod
    def revoke_refresh_token(token: str) -> None:
        """
        Revoke a specific refresh token (used during logout).
        """
        for rt in RefreshToken.objects.filter(is_revoked=False):
            if check_password(token, rt.token_hash):
                rt.is_revoked = True
                rt.save(update_fields=["is_revoked"])
                return

    @staticmethod
    def revoke_all_user_tokens(user: AuthUser) -> int:
        """
        Revoke all refresh tokens for a user (used during password change).
        Returns the number of tokens revoked.
        """
        return RefreshToken.objects.filter(user=user, is_revoked=False).update(
            is_revoked=True
        )

    @staticmethod
    def change_password(user: AuthUser, current_password: str, new_password: str) -> None:
        """
        Change a user's password.

        Raises AuthError if current_password is wrong.
        """
        if not check_password(current_password, user.password):
            raise AuthError("Current password is incorrect.")

        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])

        # Revoke all existing refresh tokens — force re-login
        AuthService.revoke_all_user_tokens(user)
