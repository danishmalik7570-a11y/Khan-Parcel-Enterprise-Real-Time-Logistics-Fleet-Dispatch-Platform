# =============================================================================
# Khan Parcel — Accounts Signals
# =============================================================================

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import User


@receiver(post_save, sender=User)
def create_user_wallet(sender: type[User], instance: User, created: bool, **kwargs: Any) -> None:
    """Automatically provision a wallet for newly registered users."""
    if created:
        try:
            from apps.payments.models import Wallet

            Wallet.objects.get_or_create(user=instance)
        except Exception:
            pass
