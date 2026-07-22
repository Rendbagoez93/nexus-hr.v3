"""
apps/shared/views_web.py

Web (Django template) views not tied to a specific business module.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def welcome_view(request: HttpRequest) -> HttpResponse:
    """Render the public marketing landing page."""
    return render(request, "index.html")


def tos_view(request: HttpRequest) -> HttpResponse:
    """Render the public Terms of Service page."""
    return render(request, "tos.html")


def privacy_view(request: HttpRequest) -> HttpResponse:
    """Render the public Privacy Policy page."""
    return render(request, "privacy.html")


@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    """Render the authenticated dashboard shell with module tabs."""
    tenant_name = (
        request.user.company.name
        if getattr(request.user, "company", None)
        else "Nexus"
    )
    return render(
        request,
        "dashboard/index.html",
        {"tenant_name": tenant_name},
    )
