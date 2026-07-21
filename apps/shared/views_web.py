"""
apps/shared/views_web.py

Web (Django template) views not tied to a specific business module.
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def welcome_view(request: HttpRequest) -> HttpResponse:
    """Render the public marketing landing page."""
    return render(request, "index.html")
