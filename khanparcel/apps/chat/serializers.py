# =============================================================================
# Khan Parcel — Chat Serializers
# =============================================================================

from __future__ import annotations

from rest_framework import serializers

from apps.chat.models import ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.name", read_only=True)
    is_me = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "order",
            "sender",
            "sender_name",
            "text",
            "attachment",
            "is_read",
            "is_me",
            "created_at",
        ]
        read_only_fields = ["id", "order", "sender", "is_read", "is_me", "created_at"]

    def get_is_me(self, obj: ChatMessage) -> bool:
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.sender_id == request.user.id
        return False


class ChatMessageCreateSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")
