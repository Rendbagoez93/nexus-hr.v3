"""
apps/shared/exceptions.py

Nexus domain exception classes and DRF exception handler.
"""

from typing import Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


class NexusBaseError(Exception):
    """
    Base exception for all Nexus domain errors.
    All subclasses must set `status_code` and `default_message`.
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message: str = "An unexpected error occurred."
    default_code: str = "error"

    def __init__(self, message: str | None = None, details: dict | None = None):
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)


class NexusNotFound(NexusBaseError):
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "Resource not found."
    default_code = "not_found"


class NexusForbidden(NexusBaseError):
    status_code = status.HTTP_403_FORBIDDEN
    default_message = "Access denied."
    default_code = "forbidden"


class NexusValidationError(NexusBaseError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "Validation failed."
    default_code = "validation_error"


class NexusConflict(NexusBaseError):
    status_code = status.HTTP_409_CONFLICT
    default_message = "Resource conflict."
    default_code = "conflict"


class NexusGone(NexusBaseError):
    status_code = status.HTTP_410_GONE
    default_message = "Resource has been deleted."
    default_code = "gone"


# ── DRF Exception Handler ───────────────────────────────────────────────────────


def nexus_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """
    Custom DRF exception handler that returns a standardized error shape
    for both Nexus domain errors and standard DRF errors.
    """

    # Handle Nexus domain errors
    if isinstance(exc, NexusBaseError):
        return Response(
            {
                "error": exc.default_code,
                "message": exc.message,
                "status": exc.status_code,
                "details": exc.details,
            },
            status=exc.status_code,
        )

    # Handle DRF built-in exceptions
    response = exception_handler(exc, context)
    if response is not None:
        error_code = getattr(exc, "default_code", "error")
        if hasattr(exc, "detail"):
            if isinstance(exc.detail, dict):
                message = "Validation failed."
                details = exc.detail
            elif isinstance(exc.detail, list):
                message = exc.detail[0] if exc.detail else "Error."
                details = {"errors": exc.detail}
            else:
                message = str(exc.detail)
                details = {}
        else:
            message = str(exc)
            details = {}

        response.data = {
            "error": error_code,
            "message": message,
            "status": response.status_code,
            "details": details,
        }

    return response
