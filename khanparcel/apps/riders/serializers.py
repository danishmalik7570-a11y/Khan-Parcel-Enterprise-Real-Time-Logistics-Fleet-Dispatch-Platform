# =============================================================================
# Khan Parcel — Riders Serializers
# =============================================================================

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.riders.models import (
    DocumentStatus,
    DocumentType,
    ReviewStatus,
    RiderDocument,
    RiderProfile,
    RiderShift,
    RiderStatus,
    Vehicle,
    VehicleType,
)


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = [
            "id",
            "vehicle_type",
            "make",
            "model",
            "year",
            "color",
            "plate_number",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RiderDocumentSerializer(serializers.ModelSerializer):
    verified_by_name = serializers.CharField(source="verified_by.name", read_only=True)

    class Meta:
        model = RiderDocument
        fields = [
            "id",
            "document_type",
            "file",
            "status",
            "rejection_reason",
            "verified_by",
            "verified_by_name",
            "verified_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "rejection_reason", "verified_by", "verified_at", "created_at", "updated_at"]


class RiderShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiderShift
        fields = [
            "id",
            "started_at",
            "ended_at",
            "total_orders",
            "total_earnings",
            "total_online_minutes",
            "created_at",
        ]
        read_only_fields = fields


class RiderProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    vehicles = VehicleSerializer(many=True, read_only=True)
    documents = RiderDocumentSerializer(many=True, read_only=True)
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()

    class Meta:
        model = RiderProfile
        fields = [
            "id",
            "user",
            "cnic_number",
            "license_number",
            "emergency_contact_name",
            "emergency_contact_phone",
            "status",
            "review_status",
            "rejection_reason",
            "lat",
            "lng",
            "heading",
            "speed",
            "battery_level",
            "is_online",
            "last_heartbeat_at",
            "shift_started_at",
            "active_orders_count",
            "rating_avg",
            "rating_count",
            "total_trips",
            "completed_trips",
            "cancelled_trips",
            "acceptance_rate",
            "completion_rate",
            "vehicles",
            "documents",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "status",
            "review_status",
            "rejection_reason",
            "lat",
            "lng",
            "heading",
            "speed",
            "battery_level",
            "is_online",
            "last_heartbeat_at",
            "shift_started_at",
            "active_orders_count",
            "rating_avg",
            "rating_count",
            "total_trips",
            "completed_trips",
            "cancelled_trips",
            "acceptance_rate",
            "completion_rate",
            "created_at",
            "updated_at",
        ]

    def get_lat(self, obj: RiderProfile) -> float | None:
        return obj.current_location.y if obj.current_location else None

    def get_lng(self, obj: RiderProfile) -> float | None:
        return obj.current_location.x if obj.current_location else None


class RiderOnboardingSerializer(serializers.Serializer):
    """Initial onboarding payload for a rider."""

    cnic_number = serializers.CharField(max_length=20)
    license_number = serializers.CharField(max_length=50)
    emergency_contact_name = serializers.CharField(max_length=150)
    emergency_contact_phone = serializers.CharField(max_length=20)
    vehicle_type = serializers.ChoiceField(choices=VehicleType.choices)
    vehicle_make = serializers.CharField(max_length=50)
    vehicle_model = serializers.CharField(max_length=50)
    vehicle_year = serializers.IntegerField(min_value=1990, max_value=2030)
    vehicle_color = serializers.CharField(max_length=30)
    vehicle_plate = serializers.CharField(max_length=30)


class RiderLocationUpdateSerializer(serializers.Serializer):
    """Real-time GPS telemetry from mobile app."""

    lat = serializers.FloatField(min_value=-90.0, max_value=90.0)
    lng = serializers.FloatField(min_value=-180.0, max_value=180.0)
    heading = serializers.FloatField(min_value=0.0, max_value=360.0, required=False, allow_null=True)
    speed = serializers.FloatField(min_value=0.0, required=False, allow_null=True)
    battery_level = serializers.IntegerField(min_value=0, max_value=100, required=False, allow_null=True)


class RiderStatusToggleSerializer(serializers.Serializer):
    """Toggle online/offline state."""

    is_online = serializers.BooleanField()


class DocumentReviewSerializer(serializers.Serializer):
    """Admin KYC document review action."""

    status = serializers.ChoiceField(choices=[DocumentStatus.APPROVED, DocumentStatus.REJECTED])
    rejection_reason = serializers.CharField(required=False, allow_blank=True, default="")
