from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.users.models import AuthUser, RefreshToken


@admin.register(AuthUser)
class AuthUserAdmin(BaseUserAdmin):
    list_display = ["email", "role", "company", "is_active", "is_staff"]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["email"]
    ordering = ["email"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Role & Company", {"fields": ("role", "company")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "role", "company"),
        }),
    )


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "device_id", "expires_at", "is_revoked", "created_at"]
    list_filter = ["is_revoked"]
    search_fields = ["user__email", "device_id"]
    ordering = ["-created_at"]
    readonly_fields = ["token_hash", "created_at"]
