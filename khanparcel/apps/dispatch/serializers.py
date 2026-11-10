# =============================================================================
# Khan Parcel — Dispatch Serializers
# =============================================================================

from __future__ import annotations

from rest_framework import serializers

from apps.dispatch.models import DispatchLog, DispatchOffer
from apps.orders.serializers import OrderSerializer


class DispatchOfferSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = DispatchOffer
        fields = [
            "id",
            "order",
            "round_number",
            "score",
            "eta_seconds",
            "distance_meters",
            "status",
            "expires_at",
            "is_expired",
            "responded_at",
            "rejection_reason",
            "created_at",
        ]
        read_only_fields = fields


class DispatchOfferRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class ManualAssignSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    rider_id = serializers.UUIDField()


class DispatchLogSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)

    class Meta:
        model = DispatchLog
        fields = [
            "id",
            "order_number",
            "round_number",
            "radius_km",
            "candidates_count",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields
