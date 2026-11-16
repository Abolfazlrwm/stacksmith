from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "documents"
    verbose_name = "Documents"

    def ready(self):
        # Import signals so they are registered at startup.
        from . import signals  # noqa: F401
