"""
apps/core/signals.py

Signal handlers for the core app (audit logging hooks).
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.models.audit import AuditLog
from apps.core.models.company import Company

# Employee signals will be added in Phase 6 when Employee model is implemented


def _get_user_id():
    """Safely get the current user ID from the current thread."""
    try:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        if hasattr(User, "current"):
            return getattr(User.current, "id", None)
    except Exception:  # noqa: BLE001
        pass
    return None


def _serialize_instance(instance) -> dict | None:
    """Serialize a Django model instance to a dict for audit logging."""
    try:
        return {
            field.name: getattr(instance, field.name, None)
            for field in instance._meta.fields
        }
    except Exception:  # noqa: BLE001
        return None


@receiver(post_save, sender=Company)
def audit_log_save(sender, instance, created, **kwargs):
    """Log all creates and updates to tracked models."""
    if getattr(instance, "_skip_audit_log", False):
        return
    AuditLog.objects.create(
        table_name=instance._meta.db_table,
        record_id=instance.pk,
        action="CREATE" if created else "UPDATE",
        before_data=None if created else _serialize_instance(instance),
        after_data=_serialize_instance(instance),
        user_id=_get_user_id(),
    )


@receiver(post_delete, sender=Company)
def audit_log_delete(sender, instance, **kwargs):
    """Log all deletes to tracked models."""
    if getattr(instance, "_skip_audit_log", False):
        return
    AuditLog.objects.create(
        table_name=instance._meta.db_table,
        record_id=instance.pk,
        action="DELETE",
        before_data=_serialize_instance(instance),
        after_data=None,
        user_id=_get_user_id(),
    )


# Note: Employee signal handlers will be added in Phase 6
