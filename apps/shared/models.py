"""
apps/shared/models.py

Shared app has no models of its own — all shared models live in apps/core/
but the abstract bases (TenantModel, SoftDeleteMixin, TimestampedModel) live here.
"""

from django.db import models

from apps.shared.mixins.soft_delete import SoftDeleteMixin
from apps.shared.mixins.timestamped import TimestampedModel


class TenantModel(SoftDeleteMixin, TimestampedModel):
    """
    Abstract base for all tenant-scoped (company-scoped) models.

    Provides:
        - company: ForeignKey to Company
        - TenantManager (filters by company automatically)
        - SoftDeleteMixin (is_active, deleted_at, deactivate())
        - TimestampedModel (created_at, updated_at)
    """

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
        db_index=True,
    )

    objects = models.Manager()

    class Meta:
        abstract = True


class TenantQuerySet(models.QuerySet):
    """QuerySet that auto-filters by company."""

    def for_company(self, company_id: int) -> "TenantQuerySet":
        return self.filter(company_id=company_id)

    def alive(self) -> "TenantQuerySet":
        return self.filter(is_active=True)


class TenantManager(models.Manager):
    """
    Custom manager that provides `.for_company(company_id)` and `.alive()`.

    Usage on a TenantModel subclass:
        class Employee(TenantModel):
            objects = TenantManager()

    Or mix with the default manager:
        objects = TenantManager()
        all_objects = models.Manager()
    """

    def get_queryset(self) -> TenantQuerySet:
        return TenantQuerySet(self.model, using=self._db)

    def for_company(self, company_id: int) -> TenantQuerySet:
        return self.get_queryset().for_company(company_id)

    def alive(self) -> TenantQuerySet:
        return self.get_queryset().alive()
