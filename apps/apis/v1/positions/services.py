"""
apps/apis/v1/positions/services.py

Position service — delegates to the app-layer service.
Provides an import path for use in views.
"""

from apps.departments.services.position_service import PositionService

__all__ = ["PositionService"]
