# =============================================================================
# Khan Parcel — Support Serializers
# =============================================================================

from __future__ import annotations

from rest_framework import serializers

from apps.support.models import SOSAlert, SupportTicket, TicketMessage


class TicketMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.name", read_only=True)

    class Meta:
        model = TicketMessage
        fields = ["id", "sender", "sender_name", "message", "attachment", "created_at"]
        read_only_fields = ["id", "sender", "created_at"]


class SupportTicketSerializer(serializers.ModelSerializer):
    messages = TicketMessageSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source="user.name", read_only=True)
    assigned_to_name = serializers.CharField(source="assigned_to.name", read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "user",
            "user_name",
            "order",
            "subject",
            "description",
            "priority",
            "status",
            "assigned_to",
            "assigned_to_name",
            "messages",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "status", "assigned_to", "created_at", "updated_at"]


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ["order", "subject", "description", "priority"]


class SOSAlertSerializer(serializers.ModelSerializer):
    rider_name = serializers.CharField(source="rider.user.name", read_only=True)
    rider_phone = serializers.CharField(source="rider.user.phone", read_only=True)
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()

    class Meta:
        model = SOSAlert
        fields = [
            "id",
            "rider",
            "rider_name",
            "rider_phone",
            "order",
            "lat",
            "lng",
            "reason",
            "resolved_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_lat(self, obj: SOSAlert) -> float | None:
        return obj.location.y if obj.location else None

    def get_lng(self, obj: SOSAlert) -> float | None:
        return obj.location.x if obj.location else None


class SOSCreateSerializer(serializers.Serializer):
    order_id = serializers.UUIDField(required=False, allow_null=True)
    lat = serializers.FloatField(required=False, allow_null=True)
    lng = serializers.FloatField(required=False, allow_null=True)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default="Accident or Security Incident")
