from __future__ import annotations

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Core app providing shared models, utilities, and middleware."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"
    verbose_name = "Core"
