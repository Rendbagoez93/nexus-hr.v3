
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.shared.mixins.timestamped import TimestampedModel


class AuditLog(TimestampedModel):

    ACTION_CHOICES = [
        ("CREATE", "Created"),
        ("UPDATE", "Updated"),
        ("DELETE", "Deleted"),
    ]

    table_name = models.CharField(max_length=255)
    record_id = models.BigIntegerField(db_index=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    # Optional: link to the user who made the change
    user_id = models.BigIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Snapshot of state before and after the change
    before_data = models.JSONField(null=True, blank=True)
    after_data = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "audit_audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["table_name", "record_id"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["user_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.table_name}.{self.record_id} [{self.action}]"
