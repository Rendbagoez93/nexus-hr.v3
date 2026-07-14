"""
apps/employees/exceptions.py

Custom exception classes for Employee operations.
"""

from rest_framework import status
from rest_framework.exceptions import APIException


class EmployeeError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Employee operation failed."
    default_code = "employee_error"

    def __init__(self, detail=None, status_code=None):
        if detail is None:
            detail = self.default_detail
        super().__init__(detail=detail)
        if status_code is not None:
            self.status_code = status_code
