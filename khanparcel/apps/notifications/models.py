# =============================================================================
# Khan Parcel — Notifications Models
# =============================================================================

from __future__ import annotations

from typing import Any

from django.db import models
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import BaseModel


class NotificationType(models.TextChoices):
    ORDER_STATUS = "ORDER_STATUS", "Order Status Update"
    DISPATCH_OFFER = "DISPATCH_OFFER", "Dispatch Offer"
    PAYMENT = "PAYMENT", "Payment & Earnings"
    SYSTEM = "SYSTEM", "System Notice"
    MARKETING = "MARKETING", "Marketing / Promo"


class Notification(BaseModel):
    """User in-app and push notification log."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.ORDER_STATUS,
        db_index=True,
    )
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "notifications_notification"
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-sent_at"]

    def __str__(self) -> str:
        return f"Notification for {self.user.name}: {self.title}"
