"""
apps/employees/apps.py

Employees app configuration.
"""

from django.apps import AppConfig


class EmployeesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.employees"
    verbose_name = "Nexus Employees"

    def ready(self):
        # Importing signals here rather than at module level avoids an import
        # loop when apps.employees is loaded before apps.attendance.
        from apps.employees import signals  # noqa: F401
