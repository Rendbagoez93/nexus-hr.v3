"""
apps/apis/v1/auth/views.py

Authentication API endpoints:
  POST /api/v1/auth/login       — obtain token pair
  POST /api/v1/auth/token/refresh  — refresh access token
  POST /api/v1/auth/logout     — revoke refresh token
  POST /api/v1/auth/password/change — change password
"""

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from pydantic import ValidationError

from apps.users.exceptions import AuthError
from apps.users.models import AuthUser
from apps.users.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
)
from apps.users.services.auth import AuthService


class LoginRateThrottle(AnonRateThrottle):
    rate = "10/minute"


class LoginView(APIView):
    """
    POST /api/v1/auth/login

    Exchange email + password for JWT access and refresh tokens.
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        try:
            schema = LoginRequest.model_validate(request.data)
        except ValidationError as e:
            return Response(
                {"detail": e.error_count() and str(e) or "Validation failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = AuthService.authenticate(schema.email, schema.password)
        except AuthError as e:
            return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        # Build JWT access token via SimpleJWT's RefreshToken
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)

        # Embed Nexus claims into the refresh token
        refresh["role"] = user.role
        if user.company_id:
            refresh["company_id"] = user.company_id

        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        return Response(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": refresh.access_token.lifetime.total_seconds(),
            },
            status=status.HTTP_200_OK,
        )


class TokenRefreshView(APIView):
    """
    POST /api/v1/auth/token/refresh

    Return a new access token from a valid SimpleJWT refresh token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from rest_framework_simplejwt.tokens import RefreshToken

        try:
            schema = RefreshRequest.model_validate(request.data)
        except ValidationError as e:
            return Response(
                {"detail": e.error_count() and str(e) or "Validation failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(schema.refresh_token)
        except TokenError as e:
            return Response(
                {"detail": f"TokenError: {e}"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except Exception as e:
            return Response(
                {"detail": f"Unexpected error validating refresh token: {e}"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Blacklist this refresh token so it cannot be reused
        try:
            refresh.blacklist()
        except AttributeError:
            pass  # BlacklistMixin may not be active

        try:
            user_id = refresh.get("user_id")
            user = AuthUser.objects.get(id=user_id)
        except AuthUser.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except Exception as e:
            return Response(
                {"detail": f"Could not get user from token: {e}"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Issue a new access token with Nexus claims
        try:
            new_refresh = RefreshToken.for_user(user)
            new_refresh["role"] = user.role
            if user.company_id:
                new_refresh["company_id"] = user.company_id

            return Response(
                {
                    "access_token": str(new_refresh.access_token),
                    "token_type": "bearer",
                    "expires_in": int(new_refresh.access_token.lifetime.total_seconds()),
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"detail": f"Could not create new token: {e}"},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout

    Blacklist the provided SimpleJWT refresh token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.exceptions import TokenError

        try:
            schema = LogoutRequest.model_validate(request.data)
        except Exception:
            return Response(
                {"detail": "refresh_token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(schema.refresh_token)
            refresh.blacklist()
        except TokenError:
            pass  # Invalid token — logout is intentionally a no-op
        except AttributeError:
            pass  # BlacklistMixin not active

        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    """
    POST /api/v1/auth/password/change

    Change the authenticated user's own password.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            schema = ChangePasswordRequest.model_validate(request.data)
        except Exception:
            return Response(
                {"detail": "Invalid request data."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            AuthService.change_password(
                user=request.user,
                current_password=schema.current_password,
                new_password=schema.new_password,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except AuthError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
