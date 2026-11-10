# =============================================================================
# Khan Parcel — Accounts Models
# =============================================================================
# User, OTPCode, Device, Address
# =============================================================================

from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from apps.core.gis_compat import gis_models
from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField

from apps.core.models import BaseModel


# ─── Role Choices ────────────────────────────────────────────────────────────

class UserRole(models.TextChoices):
    CUSTOMER = "CUSTOMER", "Customer"
    RIDER = "RIDER", "Rider"
    ADMIN = "ADMIN", "Admin"
    DISPATCHER = "DISPATCHER", "Dispatcher"
    SUPPORT = "SUPPORT", "Support"
    BUSINESS = "BUSINESS", "Business"


# ─── User Manager ───────────────────────────────────────────────────────────

class UserManager(BaseUserManager["User"]):
    """Custom manager for the User model (phone-based auth)."""

    def create_user(
        self,
        phone: str,
        name: str = "",
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        """Create and return a regular user."""
        if not phone:
            raise ValueError("Phone number is required.")
        user = self.model(phone=phone, name=name, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        phone: str,
        name: str = "Admin",
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        """Create and return a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("roles", [UserRole.ADMIN])
        if not password:
            raise ValueError("Superuser must have a password.")
        return self.create_user(phone, name, password, **extra_fields)


# ─── User Model ─────────────────────────────────────────────────────────────

class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """
    Custom user model with phone-based authentication.

    Supports multiple roles per user (e.g., a user can be both
    CUSTOMER and RIDER).
    """

    phone = PhoneNumberField(
        unique=True,
        db_index=True,
        help_text="E.164 formatted phone number (e.g., +923001234567).",
    )
    name = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text="Full name.",
    )
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Email address (optional).",
    )
    photo = models.ImageField(
        upload_to="users/photos/%Y/%m/",
        blank=True,
        null=True,
        help_text="Profile photo.",
    )
    roles = models.JSONField(
        default=list,
        help_text="User roles (e.g., ['CUSTOMER', 'RIDER']).",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this user account is active.",
    )
    is_staff = models.BooleanField(
        default=False,
        help_text="Whether this user can access the admin site.",
    )
    language = models.CharField(
        max_length=10,
        default="en",
        help_text="Preferred language code.",
    )
    last_seen_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time the user was active.",
    )

    # 2FA for staff
    totp_secret = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="TOTP secret for 2FA (staff only).",
    )
    totp_enabled = models.BooleanField(
        default=False,
        help_text="Whether 2FA is enabled.",
    )

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "accounts_user"
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["phone"], name="idx_user_phone"),
            models.Index(fields=["is_active", "created_at"], name="idx_user_active_created"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.phone})"

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_any_role(self, *roles: str) -> bool:
        """Check if user has any of the given roles."""
        return bool(set(roles) & set(self.roles))

    def add_role(self, role: str) -> None:
        """Add a role to the user."""
        if role not in self.roles:
            self.roles = list(set(self.roles) | {role})
            self.save(update_fields=["roles", "updated_at"])

    def remove_role(self, role: str) -> None:
        """Remove a role from the user."""
        if role in self.roles:
            self.roles = [r for r in self.roles if r != role]
            self.save(update_fields=["roles", "updated_at"])

    def update_last_seen(self) -> None:
        """Update the last_seen_at timestamp."""
        self.last_seen_at = timezone.now()
        self.save(update_fields=["last_seen_at"])


# ─── OTP Code ────────────────────────────────────────────────────────────────

class OTPPurpose(models.TextChoices):
    LOGIN = "LOGIN", "Login"
    REGISTER = "REGISTER", "Registration"
    RESET_PASSWORD = "RESET_PASSWORD", "Reset Password"
    VERIFY_PHONE = "VERIFY_PHONE", "Verify Phone"
    PICKUP = "PICKUP", "Pickup Verification"
    DELIVERY = "DELIVERY", "Delivery Verification"


class OTPCode(BaseModel):
    """
    OTP codes for phone verification and order operations.

    Codes are stored as SHA-256 hashes and have configurable TTL,
    max attempts, and resend cooldown.
    """

    phone = PhoneNumberField(
        db_index=True,
        help_text="Phone number the OTP was sent to.",
    )
    code_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 hash of the OTP code.",
    )
    purpose = models.CharField(
        max_length=20,
        choices=OTPPurpose.choices,
        help_text="Purpose of this OTP.",
    )
    attempts = models.PositiveSmallIntegerField(
        default=0,
        help_text="Number of verification attempts made.",
    )
    expires_at = models.DateTimeField(
        help_text="When this OTP expires.",
    )
    consumed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this OTP was successfully consumed.",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the requester.",
    )

    class Meta:
        db_table = "accounts_otp_code"
        verbose_name = "OTP Code"
        verbose_name_plural = "OTP Codes"
        indexes = [
            models.Index(fields=["phone", "purpose", "-created_at"], name="idx_otp_phone_purpose"),
            models.Index(fields=["expires_at"], name="idx_otp_expires"),
        ]

    def __str__(self) -> str:
        return f"OTP for {self.phone} ({self.purpose})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_consumed(self) -> bool:
        return self.consumed_at is not None

    @property
    def is_max_attempts(self) -> bool:
        return self.attempts >= settings.OTP_MAX_ATTEMPTS

    @property
    def is_valid(self) -> bool:
        return not self.is_expired and not self.is_consumed and not self.is_max_attempts


# ─── Device (FCM tokens) ────────────────────────────────────────────────────

class DevicePlatform(models.TextChoices):
    ANDROID = "ANDROID", "Android"
    IOS = "IOS", "iOS"
    WEB = "WEB", "Web"


class Device(BaseModel):
    """
    User device registration for push notifications.

    Each device stores an FCM token for targeted push delivery.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="devices",
        help_text="The user who owns this device.",
    )
    fcm_token = models.TextField(
        help_text="Firebase Cloud Messaging token.",
    )
    platform = models.CharField(
        max_length=10,
        choices=DevicePlatform.choices,
        help_text="Device platform.",
    )
    app_version = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Application version string.",
    )
    device_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Unique device identifier.",
    )
    last_active = models.DateTimeField(
        auto_now=True,
        help_text="Last time this device was active.",
    )

    class Meta:
        db_table = "accounts_device"
        verbose_name = "Device"
        verbose_name_plural = "Devices"
        indexes = [
            models.Index(fields=["user", "platform"], name="idx_device_user_platform"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "fcm_token"],
                name="uq_device_user_fcm_token",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user.name} - {self.platform} ({self.app_version})"


# ─── Address ─────────────────────────────────────────────────────────────────

class Address(BaseModel):
    """
    Saved addresses for users (home, work, etc.).

    Stores both text address and PostGIS Point for geospatial queries.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="addresses",
        help_text="The user who owns this address.",
    )
    label = models.CharField(
        max_length=50,
        help_text="Address label (e.g., 'Home', 'Work').",
    )
    line1 = models.CharField(
        max_length=255,
        help_text="Address line 1.",
    )
    line2 = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Address line 2 (optional).",
    )
    city = models.CharField(
        max_length=100,
        help_text="City name.",
    )
    point = gis_models.PointField(
        srid=4326,
        help_text="Geographic coordinates (longitude, latitude).",
    )
    contact_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text="Contact person name at this address.",
    )
    contact_phone = PhoneNumberField(
        blank=True,
        default="",
        help_text="Contact phone at this address.",
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the user's default address.",
    )

    class Meta:
        db_table = "accounts_address"
        verbose_name = "Address"
        verbose_name_plural = "Addresses"
        indexes = [
            models.Index(fields=["user", "is_default"], name="idx_address_user_default"),
            models.Index(fields=["point"], name="idx_address_point"),
        ]

    def __str__(self) -> str:
        return f"{self.label}: {self.line1}, {self.city}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        # Ensure only one default address per user
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
