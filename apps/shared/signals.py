"""
apps/shared/signals.py

Central signal handlers for the shared app.
"""

import structlog
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

logger = structlog.get_logger("nexus.signals")


@receiver(post_save)
def log_model_save(sender, instance, created, **kwargs):
    """Log all model saves at debug level."""
    app_label = getattr(instance._meta, "app_label", "?")
    model_name = instance._meta.model_name
    pk = instance.pk
    logger.debug(
        "model.saved",
        app=app_label,
        model=model_name,
        pk=pk,
        created=created,
    )


@receiver(post_delete)
def log_model_delete(sender, instance, **kwargs):
    """Log all model deletes at debug level."""
    app_label = getattr(instance._meta, "app_label", "?")
    model_name = instance._meta.model_name
    pk = instance.pk
    logger.debug(
        "model.deleted",
        app=app_label,
        model=model_name,
        pk=pk,
    )
