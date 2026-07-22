"""
apps/users/views_web.py

Web (session-based) views for the dashboard's authentication pages.
API/JWT login for mobile and programmatic clients lives separately in
apps/apis/v1/auth/views.py — this module backs the HTMX/Django-template
login page only.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.users.exceptions import AuthError
from apps.users.services.auth import AuthService


def login_view(request: HttpRequest) -> HttpResponse:
    """Render the login form and authenticate a session on submit."""
    if request.user.is_authenticated:
        return redirect("web-dashboard")

    if request.method != "POST":
        return render(request, "auth/login.html")

    email = request.POST.get("email", "").strip()
    password = request.POST.get("password", "")

    try:
        user = AuthService.authenticate(email, password)
    except AuthError as exc:
        messages.error(request, str(exc.detail))
        return render(request, "auth/login.html", {"email": email}, status=401)

    django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request, "Signed in successfully.")
    return redirect("web-dashboard")


def logout_view(request: HttpRequest) -> HttpResponse:
    """Log the current session out and return to the welcome page."""
    django_logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("web-home")
