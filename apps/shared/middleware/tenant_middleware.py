"""
apps/shared/middleware/tenant_middleware.py

Extracts company_id from JWT and attaches it to request object.
"""

from __future__ import annotations

import typing
from typing import TYPE_CHECKING

from django.http import HttpRequest, HttpResponse

if TYPE_CHECKING:
    from rest_framework_simplejwt.tokens import Token


class TenantMiddleware:
    """
    Middleware that extracts `company_id` from an authenticated user's JWT
    payload and attaches it as `request.company_id`.

    This allows downstream code (views, services) to read the current tenant
    without querying the database.

    Runs after AuthenticationMiddleware.
    """

    def __init__(self, get_response: "typing.Callable[[HttpRequest], HttpResponse]"):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.company_id: int | None = None

        if hasattr(request, "auth") and request.auth:
            auth_token: "Token" = request.auth
            company_id = auth_token.get("company_id")
            if company_id is not None:
                request.company_id = int(company_id)

        return self.get_response(request)
