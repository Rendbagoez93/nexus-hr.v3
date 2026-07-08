"""
apps/users/exceptions.py

User/auth-specific exception classes.
"""

from rest_framework.exceptions import APIException
from rest_framework import status


class AuthError(APIException):
    """
    Raised when an authentication or authorization operation fails.
    Maps to HTTP 401.
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication failed."
    default_code = "authentication_failed"
