from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Nexus Core"

    def ready(self):
        # Import signal handlers to register them
        import apps.core.signals  # noqa: F401
