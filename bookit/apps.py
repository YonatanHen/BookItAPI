"""Django app configuration for BookIt."""
from django.apps import AppConfig


class BookitConfig(AppConfig):
    """Registers the bookit app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "bookit"
