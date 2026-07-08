"""
apps/departments/choices.py

TextChoices for Department and Position enumerations.
"""

from django.db.models import TextChoices


class DepartmentCode(TextChoices):
    """Pre-defined department codes used across all companies."""

    HR = "HR", "Human Resource (HR)"
    FIN = "FIN", "Finance"
    ACC = "ACC", "Accounting"
    MKT = "MKT", "Marketing"
    SALES = "SALES", "Sales"
    OPS = "OPS", "Operations"
    IT = "IT", "Information Technology (IT)"
    CS = "CS", "Customer Service"
    LGL = "LGL", "Legal"
    HSE = "HSE", "Health Safety & Environment (HSE)"
    OTHER = "OTHER", "Other"


class PositionLevel(TextChoices):
    """
    Indonesian-standard job level hierarchy.
    Ordered from lowest to highest for level comparisons.
    """

    STAFF = "staff", "Staff"
    SUPERVISOR = "supervisor", "Supervisor"
    ASSISTANT_MANAGER = "assistant_manager", "Assistant Manager"
    MANAGER = "manager", "Manager"
    SENIOR_MANAGER = "senior_manager", "Senior Manager"
    GENERAL_MANAGER = "general_manager", "General Manager"
    DIRECTOR = "director", "Director"
    C_LEVEL = "c_level", "C-Level Executive"
