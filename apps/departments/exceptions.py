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


class PositionError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Position operation failed."
    default_code = "position_error"
