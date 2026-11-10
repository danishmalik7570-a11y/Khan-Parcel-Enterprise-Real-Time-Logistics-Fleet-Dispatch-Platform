# =============================================================================
# Khan Parcel — Core Utilities
# =============================================================================

from __future__ import annotations

import hashlib
import hmac
import math
import re
import secrets
import string
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import structlog
from django.conf import settings
from django.core import signing
from django.utils import timezone

logger = structlog.get_logger(__name__)


# ─── OTP Generation ─────────────────────────────────────────────────────────

def generate_otp(length: int | None = None) -> str:
    """Generate a cryptographically secure numeric OTP."""
    otp_length = length or settings.OTP_LENGTH
    return "".join(secrets.choice(string.digits) for _ in range(otp_length))


def hash_otp(otp: str) -> str:
    """Hash an OTP code using SHA-256 for secure storage."""
    return hashlib.sha256(otp.encode()).hexdigest()


def verify_otp_hash(otp: str, otp_hash: str) -> bool:
    """Verify an OTP against its hash using constant-time comparison."""
    return hmac.compare_digest(hash_otp(otp), otp_hash)


# ─── Order Code Generation ──────────────────────────────────────────────────

def generate_order_code() -> str:
    """
    Generate a unique order code in format KP-YYMMDD-XXXX.

    Example: KP-241015-A3K7
    """
    now = timezone.now()
    date_part = now.strftime("%y%m%d")
    random_part = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    return f"KP-{date_part}-{random_part}"


def generate_tracking_token() -> str:
    """Generate a URL-safe tracking token for public order tracking."""
    return secrets.token_urlsafe(32)


# ─── Geo Utilities ───────────────────────────────────────────────────────────

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points in meters.

    Uses the Haversine formula.
    """
    R = 6371000  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def estimate_eta_seconds(distance_m: float, speed_kmh: float = 25.0) -> int:
    """
    Estimate travel time in seconds using haversine distance.

    Applies a 1.4x road factor to approximate actual road distance.
    Default speed is 25 km/h (urban motorcycle).
    """
    road_distance_m = distance_m * 1.4
    speed_ms = speed_kmh * 1000 / 3600
    return int(road_distance_m / speed_ms) if speed_ms > 0 else 0


def is_within_geofence(
    lat: float, lon: float, target_lat: float, target_lon: float, radius_m: int | None = None
) -> bool:
    """Check if a point is within the configured geofence radius of a target."""
    radius = radius_m or settings.GEOFENCE_RADIUS_METERS
    distance = haversine_distance(lat, lon, target_lat, target_lon)
    return distance <= radius


def round_coordinate(coord: float, precision: int = 3) -> float:
    """Round a coordinate for caching purposes (~111m precision at 3 decimals)."""
    return round(coord, precision)


# ─── Signing / Tokens ───────────────────────────────────────────────────────

def sign_data(data: dict[str, Any], max_age: int | None = None) -> str:
    """Sign data using Django's signing framework."""
    return signing.dumps(data, compress=True)


def unsign_data(token: str, max_age: int | None = None) -> dict[str, Any] | None:
    """Verify and unsign data. Returns None if invalid or expired."""
    try:
        return signing.loads(token, max_age=max_age)
    except (signing.BadSignature, signing.SignatureExpired):
        return None


# ─── HMAC Webhook Signing ───────────────────────────────────────────────────

def compute_webhook_signature(payload: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for webhook payloads."""
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def verify_webhook_signature(payload: bytes, secret: str, signature: str) -> bool:
    """Verify a webhook HMAC-SHA256 signature using constant-time comparison."""
    expected = compute_webhook_signature(payload, secret)
    return hmac.compare_digest(expected, signature)


# ─── Phone Masking ───────────────────────────────────────────────────────────

def mask_phone(phone: str) -> str:
    """
    Mask a phone number for logging/display.

    Example: +923001234567 -> +92300***4567
    """
    if len(phone) < 7:
        return "***"
    return phone[:5] + "***" + phone[-4:]


# ─── File Validation ────────────────────────────────────────────────────────

MAGIC_BYTES: dict[str, list[bytes]] = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF"],
    "application/pdf": [b"%PDF"],
}


def validate_file_magic(file_content: bytes, expected_type: str) -> bool:
    """Validate file content by checking magic bytes."""
    magic_signatures = MAGIC_BYTES.get(expected_type, [])
    if not magic_signatures:
        return True  # Unknown type, skip magic check
    return any(file_content.startswith(sig) for sig in magic_signatures)


def sanitize_filename(filename: str) -> str:
    """Remove potentially dangerous characters from a filename."""
    # Remove path separators and null bytes
    filename = re.sub(r'[/\\:\x00]', '', filename)
    # Limit length
    name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
    name = name[:100]
    return f"{name}.{ext}" if ext else name


# ─── Money Formatting ───────────────────────────────────────────────────────

def format_money(amount_minor: int, currency: str = "PKR") -> str:
    """Format money from minor units to display string."""
    major = amount_minor / 100
    if currency == "PKR":
        return f"Rs. {major:,.0f}"
    return f"{currency} {major:,.2f}"


def minor_to_major(amount_minor: int) -> float:
    """Convert minor units to major units."""
    return amount_minor / 100


def major_to_minor(amount_major: float) -> int:
    """Convert major units to minor units (rounds to nearest integer)."""
    return round(amount_major * 100)


# ─── UUID Helpers ────────────────────────────────────────────────────────────

def is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        UUID(str(value))
        return True
    except (ValueError, AttributeError):
        return False
