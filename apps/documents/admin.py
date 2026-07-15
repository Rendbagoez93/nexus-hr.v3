"""apps/documents/admin.py"""

from django.contrib import admin

from apps.documents.models import EmployeeDocument


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = [
        "file_name",
        "doc_type",
        "employee",
        "valid_until",
        "is_verified",
        "is_active",
    ]
    list_filter = [
        "doc_type",
        "is_verified",
        "is_active",
    ]
    search_fields = [
        "file_name",
        "employee__emp_number",
        "employee__first_name",
        "employee__last_name",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    ]
    raw_id_fields = [
        "employee",
    ]
    ordering = ["-created_at"]
