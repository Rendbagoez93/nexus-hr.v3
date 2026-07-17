"""
apps/documents/exceptions.py

Custom exception classes for EmployeeDocument operations.
"""

from rest_framework import status
from rest_framework.exceptions import APIException


class DocumentError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Document operation failed."
    default_code = "document_error"

    def __init__(self, detail=None, status_code=None):
        if detail is None:
            detail = self.default_detail
        super().__init__(detail=detail)
        if status_code is not None:
            self.status_code = status_code
