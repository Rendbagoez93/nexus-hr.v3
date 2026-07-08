"""
apps/departments/admin.py

Django Admin registration for Department and Position models.
"""

from django.contrib import admin

from apps.departments.models import Department, Position


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Admin interface for Department."""

    list_display = ["name", "code", "parent", "is_active", "created_at"]
    list_filter = ["is_active", "parent"]
    search_fields = ["name", "code"]
    ordering = ["name"]
    raw_id_fields = ["parent", "company"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = [
        (
            None,
            {
                "fields": ["company", "name", "code"],
            },
        ),
        (
            "Hierarchy",
            {
                "fields": ["parent"],
                "description": "Leave blank for top-level (root) departments.",
            },
        ),
        (
            "Status",
            {
                "fields": ["is_active"],
            },
        ),
        (
            "Timestamps",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    """Admin interface for Position."""

    list_display = [
        "title",
        "department",
        "level",
        "base_salary_min",
        "base_salary_max",
        "is_active",
    ]
    list_filter = ["is_active", "level", "department"]
    search_fields = ["title"]
    ordering = ["department__name", "level", "title"]
    raw_id_fields = ["department", "company"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = [
        (
            None,
            {
                "fields": ["company", "department", "title", "level"],
            },
        ),
        (
            "Compensation",
            {
                "fields": ["base_salary_min", "base_salary_max"],
                "description": "Minimum and maximum monthly salary for this position level.",
            },
        ),
        (
            "Status",
            {
                "fields": ["is_active"],
            },
        ),
        (
            "Timestamps",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]
