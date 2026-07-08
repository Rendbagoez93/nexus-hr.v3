from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["table_name", "record_id", "action", "user_id", "ip_address", "created_at"]
    list_filter = ["action", "table_name"]
    search_fields = ["table_name", "ip_address"]
    ordering = ["-created_at"]
    readonly_fields = ["table_name", "record_id", "action", "user_id", "ip_address", "before_data", "after_data", "created_at", "updated_at"]

    def has_add_permission(self, _request):
        return False

    def has_change_permission(self, _request, _obj=None):
        return False

    def has_delete_permission(self, _request, _obj=None):
        return False
