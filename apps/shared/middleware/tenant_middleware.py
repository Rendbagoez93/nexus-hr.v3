"""
apps/shared/middleware/tenant_middleware.py

Extracts company_id from JWT and attaches it to request object.
"""

from typing import Callable

from django.http import HttpRequest, HttpResponse


class TenantMiddleware:
    """
    Middleware that extracts `company_id` from an authenticated user's JWT
    payload and attaches it as `request.company_id`.

    This allows downstream code (views, services) to read the current tenant
    without querying the database.

    Runs after AuthenticationMiddleware.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.company_id: int | None = None

        if hasattr(request, "auth") and request.auth:
            company_id = request.auth.get("company_id")
            if company_id is not None:
                request.company_id = company_id

        return self.get_response(request)
