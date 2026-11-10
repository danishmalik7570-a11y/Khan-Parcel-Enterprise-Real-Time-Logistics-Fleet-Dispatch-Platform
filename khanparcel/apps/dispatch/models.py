# =============================================================================
# Khan Parcel — Dispatch Models
# =============================================================================

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import BaseModel
from apps.orders.models import Order
from apps.riders.models import RiderProfile


class DispatchOfferStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    EXPIRED = "EXPIRED", "Expired"
    CANCELLED = "CANCELLED", "Cancelled"


class DispatchOffer(BaseModel):
    """Real-time job offer extended to an eligible candidate rider."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="dispatch_offers",
        db_index=True,
    )
    rider = models.ForeignKey(
        RiderProfile,
        on_delete=models.CASCADE,
        related_name="dispatch_offers",
        db_index=True,
    )
    round_number = models.IntegerField(default=1)
    score = models.FloatField(default=0.0)
    eta_seconds = models.IntegerField(default=300)
    distance_meters = models.FloatField(default=0.0)
    status = models.CharField(
        max_length=20,
        choices=DispatchOfferStatus.choices,
        default=DispatchOfferStatus.PENDING,
        db_index=True,
    )
    expires_at = models.DateTimeField(db_index=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "dispatch_offer"
        verbose_name = "Dispatch Offer"
        verbose_name_plural = "Dispatch Offers"
        indexes = [
            models.Index(fields=["order", "status"], name="idx_offer_order_status"),
            models.Index(fields=["rider", "status"], name="idx_offer_rider_status"),
        ]

    def __str__(self) -> str:
        return f"Offer {self.id}: Order {self.order.order_number} -> Rider {self.rider.user.name} ({self.status})"

    @property
    def is_expired(self) -> bool:
        return self.status == DispatchOfferStatus.PENDING and timezone.now() > self.expires_at


class DispatchLog(BaseModel):
    """Audit log of each dispatch round execution."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="dispatch_logs",
    )
    round_number = models.IntegerField()
    radius_km = models.FloatField()
    candidates_count = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "dispatch_log"
        verbose_name = "Dispatch Log"
        verbose_name_plural = "Dispatch Logs"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Dispatch {self.order.order_number} Round {self.round_number} (Candidates: {self.candidates_count})"
