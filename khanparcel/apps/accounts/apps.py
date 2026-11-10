from __future__ import annotations

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """User accounts, authentication, OTP, devices, and addresses."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"
    verbose_name = "Accounts"

    def ready(self) -> None:
        import apps.accounts.signals  # noqa: F401
