# =============================================================================
# Khan Parcel — Dispatch Matching Engine Service
# =============================================================================

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

import structlog
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.dispatch.models import DispatchLog, DispatchOffer, DispatchOfferStatus
from apps.orders.models import Order, OrderStatus
from apps.orders.services import OrderService
from apps.riders.models import ReviewStatus, RiderProfile, RiderStatus

logger = structlog.get_logger(__name__)


class DispatchEngine:
    """Intelligent dispatch and batch matching engine."""

    @classmethod
    def find_and_score_candidates(
        cls,
        order: Order,
        radius_km: float,
        exclude_rider_ids: list[str],
    ) -> list[dict[str, Any]]:
        # Query online approved riders
        candidates = RiderProfile.objects.filter(
            is_online=True,
            review_status=ReviewStatus.APPROVED,
            current_location__isnull=False,
            active_orders_count__lt=settings.DISPATCH_MAX_CONCURRENT_JOBS,
        ).exclude(id__in=exclude_rider_ids).select_related("user").prefetch_related("vehicles")

        scored_candidates: list[dict[str, Any]] = []
        pickup_lat = order.pickup_point.y
        pickup_lng = order.pickup_point.x

        weights = settings.DISPATCH_SCORE_WEIGHTS

        for rider in candidates:
            # Check vehicle compatibility
            has_vehicle = rider.vehicles.filter(vehicle_type=order.vehicle_type, is_active=True).exists()
            if not has_vehicle and rider.vehicles.filter(is_active=True).exists():
                # Allow bikes for small parcels, but trucks require truck
                if order.vehicle_type in ["VAN", "TRUCK"]:
                    continue

            rider_lat = rider.current_location.y
            rider_lng = rider.current_location.x
            dist_km = cls._distance_km(pickup_lat, pickup_lng, rider_lat, rider_lng)

            if dist_km > radius_km:
                continue

            # Calculate score factors (0.0 to 1.0)
            eta_minutes = (dist_km / 25.0) * 60.0  # assume 25 km/h urban speed
            eta_score = max(0.0, 1.0 - (eta_minutes / 30.0))
            rating_score = float(rider.rating_avg) / 5.0
            acceptance_score = float(rider.acceptance_rate) / 100.0
            load_score = max(0.0, 1.0 - (float(rider.active_orders_count) / float(settings.DISPATCH_MAX_CONCURRENT_JOBS)))

            composite_score = (
                weights.get("eta", 0.35) * eta_score
                + weights.get("rating", 0.20) * rating_score
                + weights.get("acceptance_rate", 0.15) * acceptance_score
                + weights.get("current_load", 0.10) * load_score
                + weights.get("idle_time", 0.10) * (1.0 if rider.active_orders_count == 0 else 0.5)
            )

            scored_candidates.append({
                "rider": rider,
                "score": round(composite_score, 4),
                "distance_meters": round(dist_km * 1000.0, 1),
                "eta_seconds": int(eta_minutes * 60),
            })

        # Sort highest score first
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        return scored_candidates

    @classmethod
    def dispatch_round(cls, order_id: str, round_num: int = 1) -> bool:
        order = Order.objects.filter(id=order_id).first()
        if not order or order.status != OrderStatus.SEARCHING_RIDER:
            logger.info("dispatch_round_skipped_not_searching", order_id=order_id)
            return False

        radii = settings.DISPATCH_RADII_KM
        max_rounds = min(len(radii), settings.DISPATCH_MAX_ROUNDS)

        if round_num > max_rounds:
            logger.warning("dispatch_all_rounds_exhausted", order_id=order_id)
            cls._notify_dispatchers_unmatched(order)
            return False

        radius = float(radii[round_num - 1])

        # Exclude riders who already received an offer for this order
        past_offers = DispatchOffer.objects.filter(order=order).values_list("rider_id", flat=True)
        candidates = cls.find_and_score_candidates(order, radius_km=radius, exclude_rider_ids=list(past_offers))

        DispatchLog.objects.create(
            order=order,
            round_number=round_num,
            radius_km=radius,
            candidates_count=len(candidates),
            metadata={"candidate_rider_ids": [str(c["rider"].id) for c in candidates[:5]]},
        )

        if not candidates:
            logger.info("dispatch_no_candidates_in_round", order_id=order_id, round=round_num, radius=radius)
            # Advance to next round immediately
            return cls.dispatch_round(order_id, round_num=round_num + 1)

        # Select top candidate
        top = candidates[0]
        rider = top["rider"]
        ttl = settings.DISPATCH_OFFER_TTL_SECONDS
        expires_at = timezone.now() + timezone.timedelta(seconds=ttl)

        offer = DispatchOffer.objects.create(
            order=order,
            rider=rider,
            round_number=round_num,
            score=top["score"],
            eta_seconds=top["eta_seconds"],
            distance_meters=top["distance_meters"],
            status=DispatchOfferStatus.PENDING,
            expires_at=expires_at,
        )

        logger.info(
            "dispatch_offer_created",
            order_id=order_id,
            rider_id=str(rider.id),
            offer_id=str(offer.id),
            round=round_num,
        )

        # Send WebSocket offer payload to rider
        cls._send_offer_to_rider(offer)

        # Schedule async timeout check task
        try:
            from apps.dispatch.tasks import check_offer_timeout
            check_offer_timeout.apply_async((str(offer.id),), countdown=ttl + 1)
        except Exception as e:
            logger.warning("failed_to_schedule_offer_timeout", error=str(e))

        return True

    @classmethod
    def accept_offer(cls, offer_id: str, rider: RiderProfile) -> Order:
        with transaction.atomic():
            offer = DispatchOffer.objects.select_for_update().get(id=offer_id, rider=rider)
            if offer.status != DispatchOfferStatus.PENDING:
                raise ValueError("Offer is no longer available.")
            if offer.is_expired:
                offer.status = DispatchOfferStatus.EXPIRED
                offer.save(update_fields=["status", "updated_at"])
                raise ValueError("Offer has expired.")

            order = Order.objects.select_for_update().get(id=offer.order_id)
            if order.status != OrderStatus.SEARCHING_RIDER:
                offer.status = DispatchOfferStatus.CANCELLED
                offer.save(update_fields=["status", "updated_at"])
                raise ValueError("Order is no longer looking for a rider.")

            # Mark offer accepted
            offer.status = DispatchOfferStatus.ACCEPTED
            offer.responded_at = timezone.now()
            offer.save(update_fields=["status", "responded_at", "updated_at"])

            # Cancel any other pending offers for this order
            DispatchOffer.objects.filter(order=order, status=DispatchOfferStatus.PENDING).exclude(id=offer.id).update(
                status=DispatchOfferStatus.CANCELLED,
                updated_at=timezone.now(),
            )

            # Assign rider to order
            order.rider = rider
            order.save(update_fields=["rider", "updated_at"])

            # Update rider status & load
            rider.active_orders_count += 1
            rider.status = RiderStatus.BUSY
            rider.save(update_fields=["active_orders_count", "status", "updated_at"])

            # Transition order status to RIDER_ASSIGNED
            assigned_order = OrderService.transition(
                order=order,
                new_status=OrderStatus.RIDER_ASSIGNED,
                changed_by=rider.user,
                note=f"Rider {rider.user.name} accepted delivery job.",
            )

            logger.info("dispatch_offer_accepted", order_id=str(order.id), rider_id=str(rider.id))
            return assigned_order

    @classmethod
    def reject_offer(cls, offer_id: str, rider: RiderProfile, reason: str = "") -> None:
        with transaction.atomic():
            offer = DispatchOffer.objects.filter(id=offer_id, rider=rider, status=DispatchOfferStatus.PENDING).first()
            if not offer:
                return
            offer.status = DispatchOfferStatus.REJECTED
            offer.rejection_reason = reason
            offer.responded_at = timezone.now()
            offer.save(update_fields=["status", "rejection_reason", "responded_at", "updated_at"])

            order = offer.order
            current_round = offer.round_number

        logger.info("dispatch_offer_rejected", offer_id=offer_id, rider_id=str(rider.id), reason=reason)
        # Advance dispatch immediately
        cls.dispatch_round(str(order.id), round_num=current_round)

    @classmethod
    def handle_offer_timeout(cls, offer_id: str) -> None:
        with transaction.atomic():
            offer = DispatchOffer.objects.filter(id=offer_id, status=DispatchOfferStatus.PENDING).first()
            if not offer:
                return
            offer.status = DispatchOfferStatus.EXPIRED
            offer.save(update_fields=["status", "updated_at"])
            order = offer.order
            current_round = offer.round_number

        logger.info("dispatch_offer_expired", offer_id=offer_id)
        # Advance dispatch to next candidate or next round
        cls.dispatch_round(str(order.id), round_num=current_round)

    @classmethod
    def manual_assign(cls, order_id: str, rider_id: str, dispatcher: User) -> Order:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id)
            if order.is_terminal:
                raise ValueError("Cannot assign rider to a finished or cancelled order.")

            rider = RiderProfile.objects.select_for_update().get(id=rider_id)
            order.rider = rider
            order.save(update_fields=["rider", "updated_at"])

            rider.active_orders_count += 1
            rider.status = RiderStatus.BUSY
            rider.save(update_fields=["active_orders_count", "status", "updated_at"])

            assigned = OrderService.transition(
                order=order,
                new_status=OrderStatus.RIDER_ASSIGNED,
                changed_by=dispatcher,
                note=f"Manually assigned by dispatcher {dispatcher.name}.",
            )

            # Cancel any open offers
            DispatchOffer.objects.filter(order=order, status=DispatchOfferStatus.PENDING).update(
                status=DispatchOfferStatus.CANCELLED,
                updated_at=timezone.now(),
            )

        logger.info("order_manually_assigned", order_id=order_id, rider_id=rider_id, dispatcher=dispatcher.email)
        return assigned

    @staticmethod
    def _send_offer_to_rider(offer: DispatchOffer) -> None:
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                return

            order = offer.order
            payload = {
                "type": "new_dispatch_offer",
                "offer_id": str(offer.id),
                "order_id": str(order.id),
                "order_number": order.order_number,
                "pickup_address": order.pickup_address,
                "dropoff_address": order.dropoff_address,
                "fare_amount": str(order.fare_amount),
                "cod_amount": str(order.cod_amount),
                "total_earnings": str(order.fare_amount),
                "eta_seconds": offer.eta_seconds,
                "distance_meters": offer.distance_meters,
                "expires_at": offer.expires_at.isoformat(),
                "ttl_seconds": settings.DISPATCH_OFFER_TTL_SECONDS,
            }

            async_to_sync(channel_layer.group_send)(f"rider_{offer.rider_id}", payload)
        except Exception as e:
            logger.warning("send_offer_failed", error=str(e))

    @staticmethod
    def _notify_dispatchers_unmatched(order: Order) -> None:
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    "dispatchers",
                    {
                        "type": "order_unmatched_alert",
                        "order_id": str(order.id),
                        "order_number": order.order_number,
                        "pickup_address": order.pickup_address,
                        "message": "All automated dispatch rounds exhausted. Manual assignment required.",
                    },
                )
        except Exception:
            pass

    @staticmethod
    def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (
            math.sin(d_lat / 2.0) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(d_lon / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c
