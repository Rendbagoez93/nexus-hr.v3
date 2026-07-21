"""
apps/shared/urls_web.py

URL routing for web (Django template) views not tied to a specific
business module.
"""

from django.urls import path

from apps.shared.views_web import welcome_view

urlpatterns = [
    path("", welcome_view, name="web-home"),
]
