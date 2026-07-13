"""
apps/employees/choices.py

TextChoices for Employee enumerations.
"""

from django.db.models import TextChoices


class EmployeeStatus(TextChoices):
    """Employee lifecycle status."""

    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"
    RESIGNED = "resigned", "Resigned"
    TERMINATED = "terminated", "Terminated"


class EmploymentType(TextChoices):
    """Type of employment contract."""

    PERMANENT = "permanent", "Permanent"
    CONTRACT = "contract", "Contract"
    PROBATION = "probation", "Probation"
    PART_TIME = "part_time", "Part-Time"
    INTERN = "intern", "Intern"


class Gender(TextChoices):
    """Gender classification."""

    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"
