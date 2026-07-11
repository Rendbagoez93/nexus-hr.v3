"""
apps/apis/v1/departments/services.py

Department service — delegates to the app-layer service.
Provides an import path for use in views.
"""

from apps.departments.services.department_service import DepartmentService

__all__ = ["DepartmentService"]
