from django.apps import AppConfig


class SharedConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.shared"
    verbose_name = "Nexus Shared"

    def ready(self):
        import apps.shared.signals  # noqa: F401
