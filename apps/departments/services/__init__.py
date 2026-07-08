"""
apps/departments/services/__init__.py

Re-exports for the departments service layer.
"""

from apps.departments.exceptions import DepartmentError, PositionError
from apps.departments.services.department_service import DepartmentService
from apps.departments.services.position_service import PositionService

__all__ = ["DepartmentError", "PositionError", "DepartmentService", "PositionService"]
