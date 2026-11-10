# =============================================================================
# Khan Parcel — Notifications Services
# =============================================================================

from __future__ import annotations

from typing import Any

import structlog
from django.conf import settings

from apps.accounts.models import Device, User
from apps.notifications.models import Notification, NotificationType

logger = structlog.get_logger(__name__)


class NotificationService:
    @classmethod
    def send_push_fcm(cls, user: User, title: str, body: str, data: dict[str, Any] | None = None) -> int:
        devices = Device.objects.filter(user=user, is_active=True)
        if not devices.exists():
            return 0

        tokens = list(devices.values_list("fcm_token", flat=True))
        data_payload = {k: str(v) for k, v in (data or {}).items()}

        if settings.FCM_ENABLED and settings.FIREBASE_CREDENTIALS_PATH:
            try:
                import firebase_admin
                from firebase_admin import messaging

                message = messaging.MulticastMessage(
                    notification=messaging.Notification(title=title, body=body),
                    data=data_payload,
                    tokens=tokens,
                )
                response = messaging.send_multicast(message)
                logger.info("fcm_push_sent", user_id=str(user.id), success=response.success_count, failure=response.failure_count)
                return response.success_count
            except Exception as e:
                logger.warning("fcm_push_failed", error=str(e))
                return 0

        # Development / console fallback
        logger.info("mock_fcm_push", user=str(user.phone), title=title, body=body, token_count=len(tokens))
        return len(tokens)

    @classmethod
    def send_sms(cls, phone: str, message: str) -> bool:
        if settings.SMS_PROVIDER == "twilio" and settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            try:
                from twilio.rest import Client
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                client.messages.create(
                    to=str(phone),
                    from_=settings.TWILIO_FROM_NUMBER,
                    body=message,
                )
                logger.info("twilio_sms_sent", phone=str(phone))
                return True
            except Exception as e:
                logger.warning("twilio_sms_failed", error=str(e))
                return False

        logger.info("mock_sms_sent", phone=str(phone), message=message)
        return True

    @classmethod
    def create_and_send(
        cls,
        user: User,
        title: str,
        body: str,
        notification_type: str = NotificationType.ORDER_STATUS,
        data: dict[str, Any] | None = None,
    ) -> Notification:
        notif = Notification.objects.create(
            user=user,
            title=title,
            body=body,
            notification_type=notification_type,
            data=data or {},
        )
        cls.send_push_fcm(user, title, body, data)
        return notif

    @classmethod
    def send_order_status_notification(cls, order: Any, new_status: str) -> None:
        status_messages = {
            "SEARCHING_RIDER": ("Order Placed", f"Finding nearest rider for order {order.order_number}..."),
            "RIDER_ASSIGNED": ("Rider Assigned", f"Rider is on the way to pick up order {order.order_number}."),
            "RIDER_ARRIVED_PICKUP": ("Rider Arrived", f"Rider has arrived at pickup for order {order.order_number}."),
            "PICKED_UP": ("Order Picked Up", f"Order {order.order_number} is on its way to destination."),
            "ARRIVED_DELIVERY": ("Rider Arrived", f"Rider is at delivery address with order {order.order_number}."),
            "DELIVERED": ("Delivered!", f"Order {order.order_number} has been safely delivered."),
            "CANCELLED": ("Order Cancelled", f"Order {order.order_number} was cancelled."),
        }

        if new_status in status_messages:
            title, body = status_messages[new_status]
            cls.create_and_send(
                user=order.customer,
                title=title,
                body=body,
                notification_type=NotificationType.ORDER_STATUS,
                data={"order_id": str(order.id), "order_number": order.order_number, "status": new_status},
            )
