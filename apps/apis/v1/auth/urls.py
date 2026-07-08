from django.urls import path

from apps.apis.v1.auth.views import (
    ChangePasswordView,
    LoginView,
    LogoutView,
    TokenRefreshView,
)

urlpatterns = [
    path("login", LoginView.as_view(), name="auth-login"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
    path("token/refresh", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("password/change", ChangePasswordView.as_view(), name="auth-password-change"),
]
