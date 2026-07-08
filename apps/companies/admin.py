from django.contrib import admin

from apps.companies.models import Company, CompanySubscription, SubscriptionPlan


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "industry",
        "subscription_tier",
        "is_active",
        "emp_number_prefix",
    ]
    list_filter = ["industry", "subscription_tier", "is_active"]
    search_fields = ["name"]
    ordering = ["name"]


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "has_attendance",
        "has_hse",
        "has_payroll",
        "price_per_employee_per_month",
        "is_active",
    ]
    list_filter = ["has_attendance", "has_hse", "has_payroll", "is_active"]
    search_fields = ["name", "code"]
    ordering = ["code"]


@admin.register(CompanySubscription)
class CompanySubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "company",
        "plan",
        "billing_period_start",
        "billing_period_end",
        "active_employee_count",
        "is_active",
    ]
    list_filter = ["plan", "is_active"]
    search_fields = ["company__name", "plan__name"]
    ordering = ["-billing_period_end"]
