"""
apps/shared/urls_web.py

URL routing for web (Django template) views not tied to a specific
business module.
"""

from django.urls import path

from apps.shared.views_web import (
    dashboard_view,
    privacy_view,
    tos_view,
    welcome_view,
)

urlpatterns = [
    path("", welcome_view, name="web-home"),
    path("dashboard/", dashboard_view, name="web-dashboard"),
    path("terms-of-service/", tos_view, name="web-tos"),
    path("privacy-policy/", privacy_view, name="web-privacy"),
]
