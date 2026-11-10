# =============================================================================
# Khan Parcel — Accounts Services
# =============================================================================
# Business logic for OTP operations, user registration, and auth.
# No business logic in views — everything goes through services.
# =============================================================================

from __future__ import annotations

from datetime import timedelta
from typing import Any

import structlog
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import OTPCode, OTPPurpose, User, UserRole
from apps.core.utils import generate_otp, hash_otp, verify_otp_hash

logger = structlog.get_logger(__name__)


class OTPService:
    """Service for OTP generation, sending, and verification."""

    @staticmethod
    def can_resend(phone: str, purpose: str) -> tuple[bool, int]:
        """
        Check if an OTP can be resent to this phone.

        Returns (can_resend, cooldown_remaining_seconds).
        """
        cooldown = settings.OTP_RESEND_COOLDOWN_SECONDS
        cutoff = timezone.now() - timedelta(seconds=cooldown)

        last_otp = (
            OTPCode.objects.filter(
                phone=phone,
                purpose=purpose,
                created_at__gte=cutoff,
            )
            .order_by("-created_at")
            .first()
        )

        if last_otp:
            elapsed = (timezone.now() - last_otp.created_at).total_seconds()
            remaining = int(cooldown - elapsed)
            return False, max(remaining, 0)

        return True, 0

    @staticmethod
    def check_rate_limit(phone: str, ip_address: str | None = None) -> bool:
        """
        Check per-phone and per-IP rate limits for OTP requests.

        Limits:
        - 3 per 10 minutes per phone
        - 10 per hour per IP
        """
        ten_min_ago = timezone.now() - timedelta(minutes=10)
        phone_count = OTPCode.objects.filter(
            phone=phone,
            created_at__gte=ten_min_ago,
        ).count()
        if phone_count >= 3:
            logger.warning("otp_rate_limit_phone", phone=str(phone), count=phone_count)
            return False

        if ip_address:
            one_hour_ago = timezone.now() - timedelta(hours=1)
            ip_count = OTPCode.objects.filter(
                ip_address=ip_address,
                created_at__gte=one_hour_ago,
            ).count()
            if ip_count >= 10:
                logger.warning("otp_rate_limit_ip", ip=ip_address, count=ip_count)
                return False

        return True

    @staticmethod
    @transaction.atomic
    def create_and_send(
        phone: str,
        purpose: str,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate an OTP, store it (hashed), and send via SMS.

        Returns a dict with status info (NOT the OTP itself, except in dev).
        """
        # Check rate limits
        if not OTPService.check_rate_limit(phone, ip_address):
            return {
                "success": False,
                "error": "RATE_LIMIT_EXCEEDED",
                "message": "Too many OTP requests. Please try again later.",
            }

        # Check resend cooldown
        can_resend, cooldown_remaining = OTPService.can_resend(phone, purpose)
        if not can_resend:
            return {
                "success": False,
                "error": "COOLDOWN_ACTIVE",
                "message": f"Please wait {cooldown_remaining} seconds before requesting a new OTP.",
                "cooldown_remaining": cooldown_remaining,
            }

        # Invalidate any existing unused OTPs for this phone/purpose
        OTPCode.objects.filter(
            phone=phone,
            purpose=purpose,
            consumed_at__isnull=True,
        ).update(consumed_at=timezone.now())

        # Generate and store
        otp_code = generate_otp()
        otp_hash = hash_otp(otp_code)
        expires_at = timezone.now() + timedelta(seconds=settings.OTP_TTL_SECONDS)

        otp_record = OTPCode.objects.create(
            phone=phone,
            code_hash=otp_hash,
            purpose=purpose,
            expires_at=expires_at,
            ip_address=ip_address,
        )

        # Send OTP via SMS provider
        OTPService._send_sms(phone, otp_code, purpose)

        logger.info("otp_created", phone=str(phone)[-4:], purpose=purpose, otp_id=str(otp_record.id))

        result: dict[str, Any] = {
            "success": True,
            "message": "OTP sent successfully.",
            "expires_in": settings.OTP_TTL_SECONDS,
            "otp_id": str(otp_record.id),
        }

        # Include OTP in dev mode for testing
        if settings.DEBUG:
            result["otp"] = otp_code  # noqa: S105 — dev only

        return result

    @staticmethod
    @transaction.atomic
    def verify(phone: str, code: str, purpose: str) -> dict[str, Any]:
        """
        Verify an OTP code.

        Returns success status and the verified OTPCode record.
        """
        otp_record = (
            OTPCode.objects.filter(
                phone=phone,
                purpose=purpose,
                consumed_at__isnull=True,
            )
            .order_by("-created_at")
            .select_for_update()
            .first()
        )

        if not otp_record:
            return {"success": False, "error": "OTP_NOT_FOUND", "message": "No valid OTP found for this phone."}

        if otp_record.is_expired:
            return {"success": False, "error": "OTP_EXPIRED", "message": "OTP has expired. Please request a new one."}

        if otp_record.is_max_attempts:
            return {
                "success": False,
                "error": "MAX_ATTEMPTS",
                "message": "Maximum verification attempts reached. Please request a new OTP.",
            }

        # Increment attempts
        otp_record.attempts += 1
        otp_record.save(update_fields=["attempts", "updated_at"])

        # Verify hash (constant-time comparison)
        if not verify_otp_hash(code, otp_record.code_hash):
            remaining = settings.OTP_MAX_ATTEMPTS - otp_record.attempts
            return {
                "success": False,
                "error": "INVALID_OTP",
                "message": f"Invalid OTP. {remaining} attempts remaining.",
                "attempts_remaining": remaining,
            }

        # Mark as consumed
        otp_record.consumed_at = timezone.now()
        otp_record.save(update_fields=["consumed_at", "updated_at"])

        logger.info("otp_verified", phone=str(phone)[-4:], purpose=purpose)

        return {"success": True, "message": "OTP verified successfully.", "otp_record": otp_record}

    @staticmethod
    def _send_sms(phone: str, otp_code: str, purpose: str) -> None:
        """
        Send OTP via configured SMS provider.

        In dev mode (console provider), the OTP is logged to console.
        """
        provider = settings.SMS_PROVIDER

        if provider == "console":
            logger.info("otp_sms_console", phone=str(phone), otp=otp_code, purpose=purpose)
            return

        if provider == "twilio":
            from apps.notifications.sms import TwilioSMSProvider

            message = f"Your Khan Parcel verification code is: {otp_code}. Valid for {settings.OTP_TTL_SECONDS // 60} minutes."
            TwilioSMSProvider().send(str(phone), message)
            return

        logger.warning("unknown_sms_provider", provider=provider)


class AuthService:
    """Service for user authentication and registration."""

    @staticmethod
    @transaction.atomic
    def register_or_login(
        phone: str,
        name: str = "",
        role: str = UserRole.CUSTOMER,
    ) -> dict[str, Any]:
        """
        Register a new user or return existing user after OTP verification.

        The actual OTP verification should be done before calling this.
        """
        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={
                "name": name,
                "roles": [role],
            },
        )

        if created:
            logger.info("user_registered", user_id=str(user.id), role=role)
        else:
            # Update last_seen
            user.update_last_seen()
            # Add role if not present
            if role and role not in user.roles:
                user.add_role(role)

        return {
            "user": user,
            "is_new": created,
        }

    @staticmethod
    def get_tokens_for_user(user: User) -> dict[str, str]:
        """Generate JWT access and refresh tokens for a user."""
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)

        # Add custom claims
        refresh["phone"] = str(user.phone)
        refresh["name"] = user.name
        refresh["roles"] = user.roles

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    @staticmethod
    @transaction.atomic
    def register_device(
        user: User,
        fcm_token: str,
        platform: str,
        app_version: str = "",
        device_id: str = "",
    ) -> None:
        """Register or update a device's FCM token."""
        from apps.accounts.models import Device

        Device.objects.update_or_create(
            user=user,
            fcm_token=fcm_token,
            defaults={
                "platform": platform,
                "app_version": app_version,
                "device_id": device_id,
            },
        )
        logger.info("device_registered", user_id=str(user.id), platform=platform)

    @staticmethod
    def deregister_device(user: User, fcm_token: str) -> None:
        """Remove a device's FCM token."""
        from apps.accounts.models import Device

        deleted, _ = Device.objects.filter(user=user, fcm_token=fcm_token).delete()
        if deleted:
            logger.info("device_deregistered", user_id=str(user.id))
