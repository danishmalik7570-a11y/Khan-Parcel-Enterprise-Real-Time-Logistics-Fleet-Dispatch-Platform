# =============================================================================
# Khan Parcel — Realtime WebSocket Consumers
# =============================================================================

from __future__ import annotations

import json
from typing import Any

import structlog
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from apps.orders.models import Order
from apps.riders.models import RiderProfile

logger = structlog.get_logger(__name__)


class TrackingConsumer(AsyncJsonWebsocketConsumer):
    """Real-time order tracking consumer for customers and riders."""

    async def connect(self) -> None:
        self.order_id = self.scope["url_route"]["kwargs"]["order_id"]
        self.room_group_name = f"order_{self.order_id}"
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        can_access = await self._can_access_order(user, self.order_id)
        if not can_access:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Send initial status
        snapshot = await self._get_order_snapshot(self.order_id)
        if snapshot:
            await self.send_json({"type": "order_snapshot", "data": snapshot})

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def order_update(self, event: dict[str, Any]) -> None:
        await self.send_json(event)

    async def rider_location_update(self, event: dict[str, Any]) -> None:
        await self.send_json(event)

    @database_sync_to_async
    def _can_access_order(self, user: Any, order_id: str) -> bool:
        if user.has_any_role("ADMIN", "DISPATCHER", "SUPPORT"):
            return True
        order = Order.objects.filter(id=order_id).first()
        if not order:
            return False
        if order.customer_id == user.id:
            return True
        if order.rider and order.rider.user_id == user.id:
            return True
        return False

    @database_sync_to_async
    def _get_order_snapshot(self, order_id: str) -> dict[str, Any] | None:
        order = Order.objects.filter(id=order_id).select_related("rider__user").first()
        if not order:
            return None
        rider_loc = None
        if order.rider and order.rider.current_location:
            rider_loc = {
                "lat": order.rider.current_location.y,
                "lng": order.rider.current_location.x,
                "heading": order.rider.heading,
                "speed": order.rider.speed,
            }
        return {
            "order_id": str(order.id),
            "order_number": order.order_number,
            "status": order.status,
            "rider": {
                "name": order.rider.user.name,
                "phone": str(order.rider.user.phone),
                "rating": str(order.rider.rating_avg),
            } if order.rider else None,
            "rider_location": rider_loc,
        }


class PublicTrackingConsumer(AsyncJsonWebsocketConsumer):
    """Anonymous public tracking link stream via secure urlsafe token."""

    async def connect(self) -> None:
        self.token = self.scope["url_route"]["kwargs"]["token"]
        order = await self._get_order_by_token(self.token)
        if not order:
            await self.close(code=4004)
            return

        self.order_id = str(order.id)
        self.room_group_name = f"order_{self.order_id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def order_update(self, event: dict[str, Any]) -> None:
        await self.send_json(event)

    async def rider_location_update(self, event: dict[str, Any]) -> None:
        await self.send_json(event)

    @database_sync_to_async
    def _get_order_by_token(self, token: str) -> Order | None:
        return Order.objects.filter(public_tracking_token=token).first()


class DispatcherConsumer(AsyncJsonWebsocketConsumer):
    """Real-time operations stream for admin and dispatchers."""

    async def connect(self) -> None:
        user = self.scope.get("user")
        if not user or not user.is_authenticated or not user.has_any_role("ADMIN", "DISPATCHER"):
            await self.close(code=4003)
            return

        self.room_group_name = "dispatchers"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        logger.info("dispatcher_ws_connected", user=user.email or str(user.phone))

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def rider_location_update(self, event: dict[str, Any]) -> None:
        await self.send_json(event)

    async def rider_status_update(self, event: dict[str, Any]) -> None:
        await self.send_json(event)

    async def order_update(self, event: dict[str, Any]) -> None:
        await self.send_json(event)

    async def order_unmatched_alert(self, event: dict[str, Any]) -> None:
        await self.send_json(event)

    async def sos_alert(self, event: dict[str, Any]) -> None:
        await self.send_json(event)


class RiderConsumer(AsyncJsonWebsocketConsumer):
    """Personal real-time stream for active rider job offers and telemetry."""

    async def connect(self) -> None:
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        profile = await self._get_rider_profile(user)
        if not profile:
            await self.close(code=4003)
            return

        self.rider_id = str(profile.id)
        self.room_group_name = f"rider_{self.rider_id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content: dict[str, Any], **kwargs: Any) -> None:
        msg_type = content.get("type")
        if msg_type == "telemetry":
            lat = content.get("lat")
            lng = content.get("lng")
            if lat is not None and lng is not None:
                await self._update_location(
                    self.rider_id,
                    float(lat),
                    float(lng),
                    content.get("heading"),
                    content.get("speed"),
                    content.get("battery"),
                )

    async def new_dispatch_offer(self, event: dict[str, Any]) -> None:
        await self.send_json(event)

    async def order_update(self, event: dict[str, Any]) -> None:
        await self.send_json(event)

    @database_sync_to_async
    def _get_rider_profile(self, user: Any) -> RiderProfile | None:
        return getattr(user, "rider_profile", None)

    @database_sync_to_async
    def _update_location(self, rider_id: str, lat: float, lng: float, heading: float | None, speed: float | None, battery: int | None) -> None:
        from apps.riders.services import RiderService
        profile = RiderProfile.objects.filter(id=rider_id).first()
        if profile:
            RiderService.update_location(profile, lat=lat, lng=lng, heading=heading, speed=speed, battery_level=battery)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """In-transit order direct messaging between customer and rider."""

    async def connect(self) -> None:
        self.order_id = self.scope["url_route"]["kwargs"]["order_id"]
        self.room_group_name = f"chat_{self.order_id}"
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content: dict[str, Any], **kwargs: Any) -> None:
        user = self.scope.get("user")
        text = content.get("message", "").strip()
        if not text:
            return

        # Save to database
        msg_obj = await self._save_message(self.order_id, user, text)

        # Broadcast to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "id": str(msg_obj["id"]),
                "sender_id": str(user.id),
                "sender_name": user.name or str(user.phone),
                "message": text,
                "timestamp": timezone.now().isoformat(),
            },
        )

    async def chat_message(self, event: dict[str, Any]) -> None:
        await self.send_json(event)

    @database_sync_to_async
    def _save_message(self, order_id: str, sender: Any, text: str) -> dict[str, Any]:
        from apps.chat.models import ChatMessage
        msg = ChatMessage.objects.create(
            order_id=order_id,
            sender=sender,
            text=text,
        )
        return {"id": msg.id}
