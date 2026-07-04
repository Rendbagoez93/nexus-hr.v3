"""
apps/shared/mixins/soft_delete.py

Soft-delete mixin for tenant-scoped models.
"""

from datetime import datetime, timezone

from django.db import models


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet that filters out soft-deleted records by default."""

    def alive(self):
        return self.filter(is_active=True)

    def dead(self):
        return self.filter(is_active=False)

    def all_with_deleted(self):
        return self.all()


class SoftDeleteMixin(models.Model):
    """
    Abstract base for soft-deletable models.

    Subclasses get:
        is_active: bool — True until deactivated
        deleted_at: datetime | None — timestamp of deactivation
        deactivate() — soft-delete method
        restore() — re-activate method
    """

    is_active = models.BooleanField(default=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        abstract = True

    def deactivate(self, deleted_by: str | None = None) -> None:
        self.is_active = False
        self.deleted_at = datetime.now(timezone.utc)
        self.save(update_fields=["is_active", "deleted_at"])

    def restore(self) -> None:
        self.is_active = True
        self.deleted_at = None
        self.save(update_fields=["is_active", "deleted_at"])
