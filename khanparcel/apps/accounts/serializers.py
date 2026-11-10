# =============================================================================
# Khan Parcel — Accounts Serializers
# =============================================================================

from __future__ import annotations

from typing import Any

from apps.core.gis_compat import Point
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import Address, Device, DevicePlatform, OTPPurpose, User, UserRole


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer that adds roles and phone to the token."""

    @classmethod
    def get_token(cls, user: User) -> Any:
        token = super().get_token(user)
        token["phone"] = str(user.phone)
        token["name"] = user.name
        token["roles"] = user.roles
        return token


# ─── OTP Serializers ─────────────────────────────────────────────────────────

class OTPRequestSerializer(serializers.Serializer):
    """Request an OTP for phone verification."""

    phone = serializers.CharField(
        max_length=20,
        help_text="E.164 phone number (e.g., +923001234567).",
    )
    purpose = serializers.ChoiceField(
        choices=[(p.value, p.label) for p in OTPPurpose if p in (OTPPurpose.LOGIN, OTPPurpose.REGISTER)],
        default=OTPPurpose.LOGIN,
        help_text="Purpose of the OTP.",
    )

    def validate_phone(self, value: str) -> str:
        """Validate phone is in E.164 format."""
        import phonenumbers

        try:
            parsed = phonenumbers.parse(value, "PK")
            if not phonenumbers.is_valid_number(parsed):
                raise serializers.ValidationError("Invalid phone number.")
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            raise serializers.ValidationError("Invalid phone number format.")


class OTPVerifySerializer(serializers.Serializer):
    """Verify an OTP and authenticate."""

    phone = serializers.CharField(max_length=20)
    code = serializers.CharField(min_length=4, max_length=8)
    purpose = serializers.ChoiceField(
        choices=[(p.value, p.label) for p in OTPPurpose if p in (OTPPurpose.LOGIN, OTPPurpose.REGISTER)],
        default=OTPPurpose.LOGIN,
    )
    name = serializers.CharField(max_length=150, required=False, default="")
    role = serializers.ChoiceField(
        choices=UserRole.choices,
        required=False,
        default=UserRole.CUSTOMER,
    )

    # Device registration (optional, included with login)
    fcm_token = serializers.CharField(required=False, default="")
    platform = serializers.ChoiceField(
        choices=DevicePlatform.choices,
        required=False,
        default="",
    )
    app_version = serializers.CharField(required=False, default="")

    def validate_phone(self, value: str) -> str:
        import phonenumbers

        try:
            parsed = phonenumbers.parse(value, "PK")
            if not phonenumbers.is_valid_number(parsed):
                raise serializers.ValidationError("Invalid phone number.")
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            raise serializers.ValidationError("Invalid phone number format.")


# ─── User Serializers ───────────────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    """Full user serializer for profile endpoints."""

    class Meta:
        model = User
        fields = [
            "id",
            "phone",
            "name",
            "email",
            "photo",
            "roles",
            "language",
            "last_seen_at",
            "created_at",
        ]
        read_only_fields = ["id", "phone", "roles", "last_seen_at", "created_at"]


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    class Meta:
        model = User
        fields = ["name", "email", "photo", "language"]


class UserListSerializer(serializers.ModelSerializer):
    """Compact user serializer for list views."""

    class Meta:
        model = User
        fields = ["id", "phone", "name", "roles", "is_active", "created_at"]


# ─── Device Serializers ─────────────────────────────────────────────────────

class DeviceSerializer(serializers.ModelSerializer):
    """Serializer for device registration."""

    class Meta:
        model = Device
        fields = ["id", "fcm_token", "platform", "app_version", "device_id", "last_active"]
        read_only_fields = ["id", "last_active"]


class DeviceRegisterSerializer(serializers.Serializer):
    """Register or update a device's FCM token."""

    fcm_token = serializers.CharField()
    platform = serializers.ChoiceField(choices=DevicePlatform.choices)
    app_version = serializers.CharField(required=False, default="")
    device_id = serializers.CharField(required=False, default="")


class DeviceDeregisterSerializer(serializers.Serializer):
    """Deregister a device's FCM token."""

    fcm_token = serializers.CharField()


# ─── Address Serializers ────────────────────────────────────────────────────

class AddressSerializer(serializers.ModelSerializer):
    """Full address serializer with lat/lng convenience fields."""

    latitude = serializers.FloatField(write_only=True, required=True)
    longitude = serializers.FloatField(write_only=True, required=True)
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()

    class Meta:
        model = Address
        fields = [
            "id",
            "label",
            "line1",
            "line2",
            "city",
            "latitude",
            "longitude",
            "lat",
            "lng",
            "contact_name",
            "contact_phone",
            "is_default",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_lat(self, obj: Address) -> float:
        return obj.point.y

    def get_lng(self, obj: Address) -> float:
        return obj.point.x

    def create(self, validated_data: dict[str, Any]) -> Address:
        lat = validated_data.pop("latitude")
        lng = validated_data.pop("longitude")
        validated_data["point"] = Point(lng, lat, srid=4326)
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance: Address, validated_data: dict[str, Any]) -> Address:
        lat = validated_data.pop("latitude", None)
        lng = validated_data.pop("longitude", None)
        if lat is not None and lng is not None:
            validated_data["point"] = Point(lng, lat, srid=4326)
        return super().update(instance, validated_data)


# ─── Auth Response Serializer ───────────────────────────────────────────────

class AuthResponseSerializer(serializers.Serializer):
    """Response serializer for successful authentication."""

    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()
    is_new = serializers.BooleanField()


class TokenRefreshResponseSerializer(serializers.Serializer):
    """Response serializer for token refresh."""

    access = serializers.CharField()
    refresh = serializers.CharField()


# ─── Staff Login Serializer ─────────────────────────────────────────────────

class StaffLoginSerializer(serializers.Serializer):
    """Staff login with email/password + optional TOTP."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    totp_code = serializers.CharField(required=False, max_length=6)
