
from django.db import models

from apps.companies.choices import INDUSTRY_CHOICES, SUBSCRIPTION_TIER_CHOICES
from apps.shared.mixins.soft_delete import SoftDeleteMixin
from apps.shared.mixins.timestamped import TimestampedModel


class Company(SoftDeleteMixin, TimestampedModel):
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
        db_table = "companies_company"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class SubscriptionPlan(TimestampedModel):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    has_attendance = models.BooleanField(default=False)
    has_hse = models.BooleanField(default=False)
    has_payroll = models.BooleanField(default=False)
    price_per_employee_per_month = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "companies_subscription_plan"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class CompanySubscription(TimestampedModel):
    company = models.OneToOneField(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="active_subscription",
    )
    plan = models.ForeignKey(
        "companies.SubscriptionPlan",
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    billing_period_start = models.DateField()
    billing_period_end = models.DateField()
    active_employee_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "companies_company_subscription"
        ordering = ["-billing_period_end"]

    def __str__(self) -> str:
        return f"{self.company.name} → {self.plan.name}"
