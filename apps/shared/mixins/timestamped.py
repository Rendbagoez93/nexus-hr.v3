"""
apps/shared/mixins/timestamped.py

Timestamp mixin for auto-managed created_at / updated_at fields.
"""

from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
