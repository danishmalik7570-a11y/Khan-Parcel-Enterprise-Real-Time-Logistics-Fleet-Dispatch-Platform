# =============================================================================
# Khan Parcel — Pricing Models
# =============================================================================

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.conf import settings
from apps.core.gis_compat import gis_models
from django.db import models
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import BaseModel
from apps.riders.models import VehicleType


class DiscountType(models.TextChoices):
    PERCENTAGE = "PERCENTAGE", "Percentage"
    FIXED = "FIXED", "Fixed Amount"


class PriceRule(BaseModel):
    """Base pricing rules for each vehicle type and zone/city."""

    vehicle_type = models.CharField(
        max_length=20,
        choices=VehicleType.choices,
        db_index=True,
    )
    city = models.CharField(max_length=50, default="Islamabad", db_index=True)
    base_fare = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("100.00"))
    base_distance_km = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("2.00"))
    per_km_rate = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("25.00"))
    per_minute_rate = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("3.00"))
    min_fare = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("100.00"))
    cancellation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("50.00"))
    free_cancellation_window_seconds = models.IntegerField(default=120)
    waiting_fee_per_minute = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("5.00"))
    free_waiting_time_minutes = models.IntegerField(default=5)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "pricing_rule"
        verbose_name = "Price Rule"
        verbose_name_plural = "Price Rules"
        unique_together = ("vehicle_type", "city")

    def __str__(self) -> str:
        return f"{self.city} - {self.vehicle_type} (Base: {self.base_fare})"


class SurgeCell(BaseModel):
    """Dynamic surge pricing index cell keyed by Uber H3 hexagon."""

    h3_index = models.CharField(max_length=25, unique=True, db_index=True)
    multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("1.00"))
    demand_count = models.IntegerField(default=0)
    supply_count = models.IntegerField(default=0)
    last_calculated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "pricing_surge_cell"
        verbose_name = "Surge Cell"
        verbose_name_plural = "Surge Cells"

    def __str__(self) -> str:
        return f"Cell {self.h3_index}: {self.multiplier}x (D:{self.demand_count}/S:{self.supply_count})"


class PromoCode(BaseModel):
    """Discount vouchers and promotional campaigns."""

    code = models.CharField(max_length=30, unique=True, db_index=True)
    description = models.CharField(max_length=255, blank=True, default="")
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENTAGE)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    max_uses = models.IntegerField(default=0, help_text="0 for unlimited")
    times_used = models.IntegerField(default=0)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "pricing_promo_code"
        verbose_name = "Promo Code"
        verbose_name_plural = "Promo Codes"

    def __str__(self) -> str:
        return f"{self.code} ({self.discount_value}{'%' if self.discount_type == DiscountType.PERCENTAGE else ' PKR'})"

    def is_valid_for_amount(self, amount: Decimal) -> tuple[bool, str]:
        now = timezone.now()
        if not self.is_active:
            return False, "Promo code is inactive."
        if now < self.valid_from or now > self.valid_to:
            return False, "Promo code has expired or is not yet valid."
        if self.max_uses > 0 and self.times_used >= self.max_uses:
            return False, "Promo code usage limit reached."
        if amount < self.min_order_amount:
            return False, f"Minimum order amount of {self.min_order_amount} PKR required."
        return True, ""

    def calculate_discount(self, order_amount: Decimal) -> Decimal:
        valid, _ = self.is_valid_for_amount(order_amount)
        if not valid:
            return Decimal("0.00")
        if self.discount_type == DiscountType.PERCENTAGE:
            discount = (order_amount * self.discount_value) / Decimal("100.00")
            if self.max_discount is not None:
                discount = min(discount, self.max_discount)
        else:
            discount = min(self.discount_value, order_amount)
        return discount.quantize(Decimal("0.01"))


class Quote(BaseModel):
    """Guaranteed price quote created before placing an order."""

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="quotes")
    pickup_point = gis_models.PointField(srid=4326)
    dropoff_point = gis_models.PointField(srid=4326)
    pickup_address = models.CharField(max_length=255)
    dropoff_address = models.CharField(max_length=255)
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices, default=VehicleType.BIKE)

    distance_km = models.DecimalField(max_digits=8, decimal_places=2)
    duration_minutes = models.DecimalField(max_digits=8, decimal_places=2)

    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    distance_price = models.DecimalField(max_digits=10, decimal_places=2)
    time_price = models.DecimalField(max_digits=10, decimal_places=2)
    surge_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("1.00"))
    surge_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    promo_code = models.ForeignKey(PromoCode, null=True, blank=True, on_delete=models.SET_NULL)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    route_polyline = models.TextField(blank=True, default="")
    expires_at = models.DateTimeField(db_index=True)
    is_accepted = models.BooleanField(default=False)

    class Meta:
        db_table = "pricing_quote"
        verbose_name = "Price Quote"
        verbose_name_plural = "Price Quotes"

    def __str__(self) -> str:
        return f"Quote {self.id}: {self.total_price} PKR ({self.vehicle_type})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at
