"""
apps/departments/exceptions.py

Custom exception classes for Department and Position operations.
"""

from rest_framework import status
from rest_framework.exceptions import APIException


class DepartmentError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Department operation failed."
    default_code = "department_error"

    def __init__(self, detail=None, status_code=None):
        if detail is None:
            detail = self.default_detail
        super().__init__(detail=detail)
        if status_code is not None:
            self.status_code = status_code


class PositionError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Position operation failed."
    default_code = "position_error"

    def __init__(self, detail=None, status_code=None):
        if detail is None:
            detail = self.default_detail
        super().__init__(detail=detail)
        if status_code is not None:
            self.status_code = status_code
