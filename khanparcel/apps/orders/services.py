# =============================================================================
# Khan Parcel — Orders Services
# =============================================================================

from __future__ import annotations

import secrets
from decimal import Decimal
from typing import Any

import structlog
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.orders.models import (
    Order,
    OrderRating,
    OrderStatus,
    OrderStatusLog,
    PaymentMethod,
    PaymentStatus,
)
from apps.pricing.models import Quote
from apps.riders.models import RiderProfile, RiderStatus

logger = structlog.get_logger(__name__)

# Valid state machine transitions
ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    OrderStatus.CREATED: [OrderStatus.SEARCHING_RIDER, OrderStatus.CANCELLED],
    OrderStatus.SEARCHING_RIDER: [OrderStatus.RIDER_ASSIGNED, OrderStatus.CANCELLED, OrderStatus.FAILED],
    OrderStatus.RIDER_ASSIGNED: [OrderStatus.RIDER_ARRIVED_PICKUP, OrderStatus.SEARCHING_RIDER, OrderStatus.CANCELLED],
    OrderStatus.RIDER_ARRIVED_PICKUP: [OrderStatus.PICKED_UP, OrderStatus.SEARCHING_RIDER, OrderStatus.CANCELLED],
    OrderStatus.PICKED_UP: [OrderStatus.ARRIVED_DELIVERY, OrderStatus.RETURNED],
    OrderStatus.ARRIVED_DELIVERY: [OrderStatus.DELIVERED, OrderStatus.RETURNED],
    OrderStatus.DELIVERED: [],
    OrderStatus.CANCELLED: [],
    OrderStatus.FAILED: [OrderStatus.SEARCHING_RIDER],
    OrderStatus.RETURNED: [],
}


class OrderService:
    @staticmethod
    def _generate_otp() -> str:
        return f"{secrets.randbelow(9000) + 1000}"

    @classmethod
    def create_from_quote(
        cls,
        quote: Quote,
        customer: User,
        sender_name: str,
        sender_phone: str,
        recipient_name: str,
        recipient_phone: str,
        instructions: str = "",
        pickup_notes: str = "",
        delivery_notes: str = "",
        parcel_description: str = "",
        parcel_weight_kg: Decimal = Decimal("1.00"),
        parcel_type: str = "SMALL_BOX",
        is_fragile: bool = False,
        requires_signature: bool = False,
        payment_method: str = PaymentMethod.COD,
        cod_amount: Decimal = Decimal("0.00"),
    ) -> Order:
        if quote.is_expired:
            raise ValueError("Quote has expired. Please calculate a new quote.")

        with transaction.atomic():
            quote.is_accepted = True
            quote.save(update_fields=["is_accepted", "updated_at"])

            order = Order.objects.create(
                customer=customer,
                quote=quote,
                vehicle_type=quote.vehicle_type,
                status=OrderStatus.SEARCHING_RIDER,
                pickup_point=quote.pickup_point,
                dropoff_point=quote.dropoff_point,
                pickup_address=quote.pickup_address,
                dropoff_address=quote.dropoff_address,
                sender_name=sender_name,
                sender_phone=sender_phone,
                recipient_name=recipient_name,
                recipient_phone=recipient_phone,
                instructions=instructions,
                pickup_notes=pickup_notes,
                delivery_notes=delivery_notes,
                parcel_description=parcel_description,
                parcel_weight_kg=parcel_weight_kg,
                parcel_type=parcel_type,
                is_fragile=is_fragile,
                requires_signature=requires_signature,
                fare_amount=quote.base_price + quote.distance_price + quote.time_price,
                surge_amount=quote.surge_amount,
                discount_amount=quote.discount_amount,
                cod_amount=cod_amount,
                total_amount=quote.total_price,
                payment_method=payment_method,
                payment_status=PaymentStatus.PENDING,
                pickup_otp=cls._generate_otp(),
                delivery_otp=cls._generate_otp(),
            )

            OrderStatusLog.objects.create(
                order=order,
                from_status=OrderStatus.CREATED,
                to_status=OrderStatus.SEARCHING_RIDER,
                changed_by=customer,
                note="Order created and dispatched for matching.",
            )

        logger.info("order_created", order_id=str(order.id), order_number=order.order_number)

        # Trigger real-time event and dispatch task
        cls._broadcast_order_event(order, "order_created")

        try:
            from apps.dispatch.tasks import dispatch_order
            dispatch_order.delay(str(order.id))
        except Exception as e:
            logger.warning("dispatch_trigger_failed", error=str(e))

        return order

    @classmethod
    def transition(
        cls,
        order: Order,
        new_status: str,
        changed_by: User | None = None,
        note: str = "",
        location: Any = None,
    ) -> Order:
        if new_status not in ALLOWED_TRANSITIONS.get(order.status, []):
            raise ValueError(f"Invalid transition from {order.status} to {new_status}.")

        old_status = order.status
        now = timezone.now()

        with transaction.atomic():
            order.status = new_status

            if new_status == OrderStatus.RIDER_ASSIGNED and not order.assigned_at:
                order.assigned_at = now
            elif new_status == OrderStatus.RIDER_ARRIVED_PICKUP and not order.arrived_pickup_at:
                order.arrived_pickup_at = now
            elif new_status == OrderStatus.PICKED_UP and not order.picked_up_at:
                order.picked_up_at = now
            elif new_status == OrderStatus.ARRIVED_DELIVERY and not order.arrived_delivery_at:
                order.arrived_delivery_at = now
            elif new_status == OrderStatus.DELIVERED and not order.delivered_at:
                order.delivered_at = now
                if order.payment_method == PaymentMethod.COD:
                    order.payment_status = PaymentStatus.PAID
                if order.rider:
                    order.rider.active_orders_count = max(0, order.rider.active_orders_count - 1)
                    order.rider.completed_trips += 1
                    order.rider.total_trips += 1
                    order.rider.save(update_fields=["active_orders_count", "completed_trips", "total_trips", "updated_at"])

            order.save()

            OrderStatusLog.objects.create(
                order=order,
                from_status=old_status,
                to_status=new_status,
                changed_by=changed_by,
                note=note,
                location=location,
            )

        logger.info("order_status_transitioned", order_id=str(order.id), old=old_status, new=new_status)
        cls._broadcast_order_event(order, f"order_status_{new_status.lower()}")

        # Send push notification
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send_order_status_notification(order, new_status)
        except Exception:
            pass

        return order

    @classmethod
    def verify_pickup_otp(cls, order: Order, code: str, proof_file: Any = None) -> Order:
        if order.status != OrderStatus.RIDER_ARRIVED_PICKUP:
            raise ValueError("Order must be at pickup location to verify pickup.")
        if order.pickup_otp != code.strip():
            raise ValueError("Invalid pickup OTP code.")

        if proof_file:
            order.proof_of_pickup = proof_file
            order.save(update_fields=["proof_of_pickup", "updated_at"])

        return cls.transition(order, OrderStatus.PICKED_UP, note="Pickup OTP verified by sender.")

    @classmethod
    def verify_delivery_otp(
        cls,
        order: Order,
        code: str,
        proof_file: Any = None,
        signature_file: Any = None,
        recipient_name: str = "",
    ) -> Order:
        if order.status != OrderStatus.ARRIVED_DELIVERY:
            raise ValueError("Order must be at delivery location to complete.")
        if order.delivery_otp != code.strip():
            raise ValueError("Invalid delivery OTP code.")

        if proof_file:
            order.proof_of_delivery = proof_file
        if signature_file:
            order.signature_image = signature_file
        if recipient_name:
            order.recipient_signature_name = recipient_name
        order.save()

        # Trigger payments settlement for COD & Rider earnings
        delivered_order = cls.transition(order, OrderStatus.DELIVERED, note="Delivery OTP verified and completed.")
        try:
            from apps.payments.services import PaymentService
            PaymentService.settle_order_payment(delivered_order)
        except Exception as e:
            logger.error("payment_settlement_failed", order_id=str(order.id), error=str(e))

        return delivered_order

    @classmethod
    def cancel_order(cls, order: Order, cancelled_by: User, reason: str = "") -> Order:
        if order.is_terminal:
            raise ValueError("Cannot cancel an order that is already completed or cancelled.")

        with transaction.atomic():
            order.cancellation_reason = reason
            order.cancelled_by = cancelled_by
            order.cancelled_at = timezone.now()
            order.save(update_fields=["cancellation_reason", "cancelled_by", "cancelled_at", "updated_at"])

            if order.rider:
                order.rider.active_orders_count = max(0, order.rider.active_orders_count - 1)
                order.rider.cancelled_trips += 1
                order.rider.save(update_fields=["active_orders_count", "cancelled_trips", "updated_at"])

            cls.transition(order, OrderStatus.CANCELLED, changed_by=cancelled_by, note=f"Cancelled: {reason}")

        return order

    @classmethod
    def rate_order(cls, order: Order, customer: User, score: int, comment: str = "", tags: str = "") -> OrderRating:
        if order.status != OrderStatus.DELIVERED:
            raise ValueError("Only completed orders can be reviewed.")
        if order.customer != customer:
            raise ValueError("Only the customer can rate this order.")
        if hasattr(order, "rating"):
            raise ValueError("This order has already been rated.")

        with transaction.atomic():
            rating = OrderRating.objects.create(
                order=order,
                customer=customer,
                rider=order.rider,
                score=score,
                comment=comment,
                tags=tags,
            )

            # Update rider rating average
            rider = order.rider
            if rider:
                total_ratings = rider.rating_count + 1
                new_avg = ((rider.rating_avg * rider.rating_count) + Decimal(score)) / Decimal(total_ratings)
                rider.rating_avg = new_avg.quantize(Decimal("0.01"))
                rider.rating_count = total_ratings
                rider.save(update_fields=["rating_avg", "rating_count", "updated_at"])

        return rating

    @staticmethod
    def _broadcast_order_event(order: Order, event_type: str) -> None:
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                return

            payload = {
                "type": "order_update",
                "event": event_type,
                "order_id": str(order.id),
                "order_number": order.order_number,
                "status": order.status,
                "rider_id": str(order.rider_id) if order.rider_id else None,
                "customer_id": str(order.customer_id),
                "timestamp": timezone.now().isoformat(),
            }

            async_to_sync(channel_layer.group_send)("dispatchers", payload)
            async_to_sync(channel_layer.group_send)(f"order_{order.id}", payload)
            async_to_sync(channel_layer.group_send)(f"customer_{order.customer_id}", payload)
            if order.rider_id:
                async_to_sync(channel_layer.group_send)(f"rider_{order.rider_id}", payload)
        except Exception as e:
            logger.warning("broadcast_order_event_failed", error=str(e))
