"""
apps/core/models/subscription.py

Subscription models — SubscriptionPlan and CompanySubscription.
"""

from django.db import models

from apps.shared.mixins.timestamped import TimestampedModel


class SubscriptionPlan(TimestampedModel):
    """
    Defines a subscription plan (tier) with module feature flags.
    """

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    has_attendance = models.BooleanField(default=False)
    has_hse = models.BooleanField(default=False)
    has_payroll = models.BooleanField(default=False)
    price_per_employee_per_month = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_subscription_plan"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class CompanySubscription(TimestampedModel):
    """
    Links a Company to its active SubscriptionPlan with billing metadata.
    """

    company = models.OneToOneField(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="active_subscription",
    )
    plan = models.ForeignKey(
        "core.SubscriptionPlan",
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    billing_period_start = models.DateField()
    billing_period_end = models.DateField()
    active_employee_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_company_subscription"
        ordering = ["-billing_period_end"]

    def __str__(self) -> str:
        return f"{self.company.name} → {self.plan.name}"
