# =============================================================================
# Khan Parcel — Riders Models
# =============================================================================

from __future__ import annotations

from typing import Any

from django.conf import settings
from apps.core.gis_compat import Point, gis_models
from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField

from apps.accounts.models import User
from apps.core.models import BaseModel


class RiderStatus(models.TextChoices):
    OFFLINE = "OFFLINE", "Offline"
    AVAILABLE = "AVAILABLE", "Available"
    BUSY = "BUSY", "Busy"
    SUSPENDED = "SUSPENDED", "Suspended"


class ReviewStatus(models.TextChoices):
    INCOMPLETE = "INCOMPLETE", "Incomplete"
    PENDING_REVIEW = "PENDING_REVIEW", "Pending Review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class VehicleType(models.TextChoices):
    BIKE = "BIKE", "Motorcycle / Bike"
    CAR = "CAR", "Car"
    VAN = "VAN", "Delivery Van"
    TRUCK = "TRUCK", "Mini Truck"


class DocumentType(models.TextChoices):
    CNIC_FRONT = "CNIC_FRONT", "CNIC Front"
    CNIC_BACK = "CNIC_BACK", "CNIC Back"
    DRIVING_LICENSE = "DRIVING_LICENSE", "Driving License"
    VEHICLE_REGISTRATION = "VEHICLE_REGISTRATION", "Vehicle Registration"
    POLICE_VERIFICATION = "POLICE_VERIFICATION", "Police Verification"


class DocumentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class RiderProfile(BaseModel):
    """
    Rider profile extending the User model with dispatch and KYC information.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="rider_profile",
    )
    cnic_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="CNIC number (e.g. 61101-1234567-1)",
    )
    license_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Driving license number",
    )
    emergency_contact_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )
    emergency_contact_phone = PhoneNumberField(
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=RiderStatus.choices,
        default=RiderStatus.OFFLINE,
        db_index=True,
    )
    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING_REVIEW,
        db_index=True,
    )
    rejection_reason = models.TextField(blank=True, default="")
    current_location = gis_models.PointField(
        srid=4326,
        null=True,
        blank=True,
        db_index=True,
        help_text="Current GPS location (Point(lng, lat))",
    )
    heading = models.FloatField(null=True, blank=True, help_text="Bearing 0-360")
    speed = models.FloatField(null=True, blank=True, help_text="Speed in km/h")
    battery_level = models.IntegerField(null=True, blank=True, help_text="0-100%")
    is_online = models.BooleanField(default=False, db_index=True)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True, db_index=True)
    shift_started_at = models.DateTimeField(null=True, blank=True)
    active_orders_count = models.IntegerField(default=0)

    # Operational metrics
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    rating_count = models.IntegerField(default=0)
    total_trips = models.IntegerField(default=0)
    completed_trips = models.IntegerField(default=0)
    cancelled_trips = models.IntegerField(default=0)
    acceptance_rate = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)

    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_riders",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "riders_profile"
        verbose_name = "Rider Profile"
        verbose_name_plural = "Rider Profiles"
        indexes = [
            models.Index(fields=["status", "is_online"], name="idx_rider_status_online"),
            models.Index(fields=["review_status"], name="idx_rider_review_status"),
            models.Index(fields=["last_heartbeat_at"], name="idx_rider_heartbeat"),
        ]

    def __str__(self) -> str:
        return f"Rider: {self.user.name or self.user.phone} ({self.status})"

    def update_location(self, lat: float, lng: float, heading: float | None = None, speed: float | None = None, battery: int | None = None) -> None:
        """Update current position, timestamp, and optional telemetry."""
        self.current_location = Point(lng, lat, srid=4326)
        if heading is not None:
            self.heading = heading
        if speed is not None:
            self.speed = speed
        if battery is not None:
            self.battery_level = battery
        self.last_heartbeat_at = timezone.now()
        self.save(update_fields=["current_location", "heading", "speed", "battery_level", "last_heartbeat_at", "updated_at"])

    def go_online(self) -> None:
        """Set rider online and start shift if not already active."""
        if self.review_status != ReviewStatus.APPROVED:
            raise ValueError("Rider account is not approved yet.")
        now = timezone.now()
        self.is_online = True
        self.status = RiderStatus.AVAILABLE if self.active_orders_count == 0 else RiderStatus.BUSY
        self.last_heartbeat_at = now
        if not self.shift_started_at:
            self.shift_started_at = now
            RiderShift.objects.create(rider=self, started_at=now)
        self.save(update_fields=["is_online", "status", "last_heartbeat_at", "shift_started_at", "updated_at"])

    def go_offline(self) -> None:
        """Set rider offline and end ongoing shift."""
        now = timezone.now()
        self.is_online = False
        self.status = RiderStatus.OFFLINE
        if self.shift_started_at:
            # End open shift
            open_shift = RiderShift.objects.filter(rider=self, ended_at__isnull=True).order_by("-started_at").first()
            if open_shift:
                open_shift.ended_at = now
                duration = int((now - open_shift.started_at).total_seconds() / 60)
                open_shift.total_online_minutes = max(duration, 0)
                open_shift.save(update_fields=["ended_at", "total_online_minutes", "updated_at"])
            self.shift_started_at = None
        self.save(update_fields=["is_online", "status", "shift_started_at", "updated_at"])


class Vehicle(BaseModel):
    """Vehicle registered to a rider."""

    rider = models.ForeignKey(
        RiderProfile,
        on_delete=models.CASCADE,
        related_name="vehicles",
    )
    vehicle_type = models.CharField(
        max_length=20,
        choices=VehicleType.choices,
        default=VehicleType.BIKE,
    )
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.IntegerField(default=2020)
    color = models.CharField(max_length=30)
    plate_number = models.CharField(max_length=30, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "riders_vehicle"
        verbose_name = "Vehicle"
        verbose_name_plural = "Vehicles"

    def __str__(self) -> str:
        return f"{self.vehicle_type} - {self.plate_number} ({self.make} {self.model})"


class RiderDocument(BaseModel):
    """KYC / Verification document uploaded by rider."""

    rider = models.ForeignKey(
        RiderProfile,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
    )
    file = models.FileField(upload_to="riders/documents/%Y/%m/")
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
        db_index=True,
    )
    rejection_reason = models.TextField(blank=True, default="")
    verified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_documents",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "riders_document"
        verbose_name = "Rider Document"
        verbose_name_plural = "Rider Documents"
        unique_together = ("rider", "document_type")

    def __str__(self) -> str:
        return f"{self.rider.user.name} - {self.document_type} ({self.status})"


class RiderShift(BaseModel):
    """Historical record of rider work shifts."""

    rider = models.ForeignKey(
        RiderProfile,
        on_delete=models.CASCADE,
        related_name="shifts",
    )
    started_at = models.DateTimeField(db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    total_orders = models.IntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_online_minutes = models.IntegerField(default=0)

    class Meta:
        db_table = "riders_shift"
        verbose_name = "Rider Shift"
        verbose_name_plural = "Rider Shifts"
        indexes = [
            models.Index(fields=["rider", "started_at"], name="idx_shift_rider_start"),
        ]

    def __str__(self) -> str:
        return f"Shift {self.rider.user.name}: {self.started_at.strftime('%Y-%m-%d %H:%M')}"
