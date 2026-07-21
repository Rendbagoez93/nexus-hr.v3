"""
apps/users/urls_web.py

URL routing for web (Django template) authentication views.
"""

from django.urls import path

from apps.users.views_web import login_view, logout_view

urlpatterns = [
    path("login/", login_view, name="web-login"),
    path("logout/", logout_view, name="web-logout"),
]
