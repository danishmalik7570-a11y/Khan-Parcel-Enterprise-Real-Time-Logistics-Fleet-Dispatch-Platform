# =============================================================================
# Khan Parcel — Orders Models
# =============================================================================

from __future__ import annotations

import secrets
from decimal import Decimal
from typing import Any

from django.conf import settings
from apps.core.gis_compat import gis_models
from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField

from apps.accounts.models import User
from apps.core.models import BaseModel
from apps.pricing.models import Quote
from apps.riders.models import RiderProfile, VehicleType


class OrderStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    SEARCHING_RIDER = "SEARCHING_RIDER", "Searching Rider"
    RIDER_ASSIGNED = "RIDER_ASSIGNED", "Rider Assigned"
    RIDER_ARRIVED_PICKUP = "RIDER_ARRIVED_PICKUP", "Rider Arrived at Pickup"
    PICKED_UP = "PICKED_UP", "Picked Up"
    ARRIVED_DELIVERY = "ARRIVED_DELIVERY", "Arrived at Delivery"
    DELIVERED = "DELIVERED", "Delivered"
    CANCELLED = "CANCELLED", "Cancelled"
    FAILED = "FAILED", "Failed"
    RETURNED = "RETURNED", "Returned to Sender"


class PaymentMethod(models.TextChoices):
    COD = "COD", "Cash on Delivery"
    WALLET = "WALLET", "Khan Wallet"
    CARD = "CARD", "Debit/Credit Card"
    EASYPAISA = "EASYPAISA", "Easypaisa"
    JAZZCASH = "JAZZCASH", "JazzCash"


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    AUTHORIZED = "AUTHORIZED", "Authorized"
    PAID = "PAID", "Paid"
    REFUNDED = "REFUNDED", "Refunded"
    FAILED = "FAILED", "Failed"


class ParcelType(models.TextChoices):
    DOCUMENT = "DOCUMENT", "Document / Envelopes"
    SMALL_BOX = "SMALL_BOX", "Small Box (< 2kg)"
    MEDIUM_BOX = "MEDIUM_BOX", "Medium Box (2 - 5kg)"
    LARGE_PARCEL = "LARGE_PARCEL", "Large Parcel (> 5kg)"
    FOOD = "FOOD", "Food / Groceries"
    FRAGILE = "FRAGILE", "Fragile / Electronics"
    CUSTOM = "CUSTOM", "Other Goods"


def generate_order_number() -> str:
    date_str = timezone.now().strftime("%Y%m%d")
    random_hex = secrets.token_hex(3).upper()
    return f"KP-{date_str}-{random_hex}"


def generate_tracking_token() -> str:
    return secrets.token_urlsafe(12)


class Order(BaseModel):
    """Primary delivery order entity representing full lifecycle."""

    order_number = models.CharField(
        max_length=32,
        unique=True,
        default=generate_order_number,
        db_index=True,
    )
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="customer_orders",
        db_index=True,
    )
    rider = models.ForeignKey(
        RiderProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
        db_index=True,
    )
    quote = models.ForeignKey(
        Quote,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    status = models.CharField(
        max_length=30,
        choices=OrderStatus.choices,
        default=OrderStatus.CREATED,
        db_index=True,
    )
    vehicle_type = models.CharField(
        max_length=20,
        choices=VehicleType.choices,
        default=VehicleType.BIKE,
    )

    # Locations
    pickup_point = gis_models.PointField(srid=4326, db_index=True)
    dropoff_point = gis_models.PointField(srid=4326, db_index=True)
    pickup_address = models.CharField(max_length=255)
    dropoff_address = models.CharField(max_length=255)

    # Sender & Recipient Contacts
    sender_name = models.CharField(max_length=150)
    sender_phone = PhoneNumberField()
    recipient_name = models.CharField(max_length=150)
    recipient_phone = PhoneNumberField()

    # Notes & Instructions
    instructions = models.TextField(blank=True, default="")
    pickup_notes = models.TextField(blank=True, default="")
    delivery_notes = models.TextField(blank=True, default="")

    # Parcel details
    parcel_description = models.CharField(max_length=255, blank=True, default="")
    parcel_weight_kg = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1.00"))
    parcel_type = models.CharField(max_length=30, choices=ParcelType.choices, default=ParcelType.SMALL_BOX)
    is_fragile = models.BooleanField(default=False)
    requires_signature = models.BooleanField(default=False)

    # Financials
    fare_amount = models.DecimalField(max_digits=10, decimal_places=2)
    surge_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    cod_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), help_text="Cash to collect from recipient for merchant goods")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.COD)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)

    # Verification OTPs
    pickup_otp = models.CharField(max_length=6, blank=True, default="")
    delivery_otp = models.CharField(max_length=6, blank=True, default="")

    # Proofs
    proof_of_pickup = models.ImageField(upload_to="orders/proofs/%Y/%m/", null=True, blank=True)
    proof_of_delivery = models.ImageField(upload_to="orders/proofs/%Y/%m/", null=True, blank=True)
    signature_image = models.ImageField(upload_to="orders/signatures/%Y/%m/", null=True, blank=True)
    recipient_signature_name = models.CharField(max_length=150, blank=True, default="")

    # Cancellation
    cancellation_reason = models.TextField(blank=True, default="")
    cancelled_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="cancelled_orders")
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # Timestamps for SLA tracking
    assigned_at = models.DateTimeField(null=True, blank=True)
    arrived_pickup_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    arrived_delivery_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    # Public tracking web link
    public_tracking_token = models.CharField(max_length=32, unique=True, default=generate_tracking_token, db_index=True)

    class Meta:
        db_table = "orders_order"
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        indexes = [
            models.Index(fields=["status", "created_at"], name="idx_order_status_created"),
            models.Index(fields=["customer", "status"], name="idx_order_cust_status"),
            models.Index(fields=["rider", "status"], name="idx_order_rider_status"),
        ]

    def __str__(self) -> str:
        return f"{self.order_number} ({self.status}) - {self.total_amount} PKR"

    @property
    def is_terminal(self) -> bool:
        return self.status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED, OrderStatus.FAILED, OrderStatus.RETURNED]


class OrderStatusLog(BaseModel):
    """Audit log of state changes for an order."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_logs",
    )
    from_status = models.CharField(max_length=30)
    to_status = models.CharField(max_length=30)
    changed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=255, blank=True, default="")
    location = gis_models.PointField(srid=4326, null=True, blank=True)

    class Meta:
        db_table = "orders_status_log"
        verbose_name = "Order Status Log"
        verbose_name_plural = "Order Status Logs"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.order.order_number}: {self.from_status} -> {self.to_status}"


class OrderRating(BaseModel):
    """Customer review of delivery and rider performance."""

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="rating",
    )
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="given_ratings")
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name="ratings")
    score = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)], help_text="1 to 5 stars")
    comment = models.TextField(blank=True, default="")
    tags = models.CharField(max_length=255, blank=True, default="", help_text="Comma-separated praise or issue tags")

    class Meta:
        db_table = "orders_rating"
        verbose_name = "Order Rating"
        verbose_name_plural = "Order Ratings"

    def __str__(self) -> str:
        return f"Rating {self.score}* for {self.order.order_number}"
