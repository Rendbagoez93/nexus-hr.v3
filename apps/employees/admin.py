"""
apps/employees/admin.py

Django admin configuration for the Employee model.
"""

from django.contrib import admin

from apps.employees.models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        "emp_number",
        "first_name",
        "last_name",
        "company",
        "department",
        "status",
        "employment_type",
        "join_date",
        "is_active",
    ]
    list_filter = [
        "status",
        "employment_type",
        "gender",
        "company",
        "department",
        "is_active",
    ]
    search_fields = [
        "emp_number",
        "first_name",
        "last_name",
        "email",
        "phone",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    ]
    raw_id_fields = [
        "company",
        "user",
        "department",
        "position",
        "direct_manager",
    ]
    ordering = ["company", "emp_number"]
