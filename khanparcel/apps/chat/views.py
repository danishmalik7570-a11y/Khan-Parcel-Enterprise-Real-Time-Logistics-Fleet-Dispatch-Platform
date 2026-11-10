# =============================================================================
# Khan Parcel — Chat Views
# =============================================================================

from __future__ import annotations

from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from apps.chat.models import ChatMessage
from apps.chat.serializers import ChatMessageCreateSerializer, ChatMessageSerializer
from apps.orders.models import Order


class OrderChatMessagesView(generics.ListCreateAPIView):
    """List and send in-app chat messages for an order."""

    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self) -> Any:
        order_id = self.kwargs["order_id"]
        order = get_object_or_404(Order, id=order_id)
        # Mark incoming messages as read
        ChatMessage.objects.filter(order=order).exclude(sender=self.request.user).update(is_read=True)
        return ChatMessage.objects.filter(order=order).select_related("sender").order_by("created_at")

    @extend_schema(request=ChatMessageCreateSerializer, responses={201: ChatMessageSerializer}, tags=["Chat"], summary="Send Message")
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        order_id = self.kwargs["order_id"]
        order = get_object_or_404(Order, id=order_id)

        # Access control
        if not (request.user == order.customer or (order.rider and request.user == order.rider.user) or request.user.has_any_role("ADMIN", "DISPATCHER")):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        text = request.data.get("text", "").strip()
        attachment = request.FILES.get("attachment")

        if not text and not attachment:
            return Response({"error": {"code": "EMPTY_MESSAGE", "message": "Text or attachment is required."}}, status=status.HTTP_400_BAD_REQUEST)

        msg = ChatMessage.objects.create(
            order=order,
            sender=request.user,
            text=text,
            attachment=attachment,
        )

        # Broadcast via WebSocket channel layer
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"chat_{order.id}",
                    {
                        "type": "chat_message",
                        "id": str(msg.id),
                        "sender_id": str(request.user.id),
                        "sender_name": request.user.name or str(request.user.phone),
                        "message": text,
                        "timestamp": timezone.now().isoformat(),
                    },
                )
        except Exception:
            pass

        return Response(ChatMessageSerializer(msg, context={"request": request}).data, status=status.HTTP_201_CREATED)
