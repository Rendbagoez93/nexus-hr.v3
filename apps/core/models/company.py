"""
apps/core/models/company.py

Company model — the tenant boundary.
"""

from django.db import models

from apps.shared.mixins.soft_delete import SoftDeleteMixin
from apps.shared.mixins.timestamped import TimestampedModel


class Company(SoftDeleteMixin, TimestampedModel):
    """
    Represents a tenant (client company) in Nexus.

    The tenant boundary — every employee, department, and record belongs to a Company.
    """

    INDUSTRY_CHOICES = [
        ("manufacturing", "Manufacturing"),
        ("construction", "Construction"),
        ("mining", "Mining"),
        ("office", "Office / General"),
    ]

    SUBSCRIPTION_TIER_CHOICES = [
        ("core", "Core"),
        ("attendance", "Attendance & Leave"),
        ("hse", "HSE + Man Hours"),
        ("payroll", "Full Suite"),
    ]

    name = models.CharField(max_length=255)
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES, default="office")
    subscription_tier = models.CharField(
        max_length=50, choices=SUBSCRIPTION_TIER_CHOICES, default="core"
    )
    is_active = models.BooleanField(default=True, db_index=True)

    # Geofence for mobile clock-in/out validation
    geofence_latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    geofence_longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    geofence_radius_meters = models.IntegerField(default=100)

    # Company prefix for employee numbers (e.g., "NXS", "ACME")
    emp_number_prefix = models.CharField(max_length=10, default="NXS")

    class Meta:
        db_table = "core_company"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
