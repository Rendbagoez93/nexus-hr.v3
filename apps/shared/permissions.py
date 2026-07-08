"""
apps/shared/permissions.py

Cross-module DRF permission classes.
"""

from rest_framework import permissions


class IsPlatformAdmin(permissions.BasePermission):
    message = "Platform admin access required."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class IsHRAdmin(permissions.BasePermission):
    message = "HR Admin access required."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "hr_admin"
        )


class IsManagerOrAbove(permissions.BasePermission):
    message = "Manager-level access required."

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        role = getattr(request.user, "role", None)
        return role in ("platform_admin", "hr_admin", "manager")


class IsOwnerOrHRAdmin(permissions.BasePermission):
    message = "You can only access your own resource or need HR Admin privileges."

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if getattr(user, "role", None) in ("platform_admin", "hr_admin"):
            return True
        # Check if obj has user FK
        obj_user_id = getattr(obj, "user_id", None) or getattr(obj, "user", None)
        return getattr(user, "id", None) == obj_user_id


class IsHSEOfficerOrAbove(permissions.BasePermission):
    message = "HSE Officer-level access required."

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        role = getattr(request.user, "role", None)
        return role in ("platform_admin", "hr_admin", "manager", "hse_officer")


class IsEmployee(permissions.BasePermission):
    message = "Employee access required."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)


def HasModuleAccess(module_flag: str):
    """
    Factory: create a permission class that gates access by subscription module.

    Usage:
        permission_classes = [HasModuleAccess("has_attendance")]

    module_flag: the SubscriptionPlan field name to check.
    """

    class _HasModuleAccess(permissions.BasePermission):
        message = f"Module '{module_flag}' is not included in your subscription."

        def has_permission(self, request, view) -> bool:
            if not (request.user and request.user.is_authenticated):
                return False
            if getattr(request.user, "is_superuser", False):
                return True
            company = getattr(request.user, "company", None)
            if not company:
                return False
            subscription = (
                company.subscriptions.filter(is_active=True)
                .exclude(billing_period_end__isnull=True)
                .order_by("-billing_period_start")
                .first()
            )
            if not subscription:
                return False
            return bool(getattr(subscription.plan, module_flag, False))

    return _HasModuleAccess
