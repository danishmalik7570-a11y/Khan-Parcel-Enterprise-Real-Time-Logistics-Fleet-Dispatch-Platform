# =============================================================================
# Khan Parcel — Notifications Serializers
# =============================================================================

from __future__ import annotations

from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "body",
            "notification_type",
            "data",
            "is_read",
            "sent_at",
            "created_at",
        ]
        read_only_fields = fields
