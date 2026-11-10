# =============================================================================
# Khan Parcel — Orders Views
# =============================================================================

from __future__ import annotations

from typing import Any

from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.permissions import IsAdminOrDispatcher
from apps.orders.models import Order, OrderRating, OrderStatus
from apps.orders.serializers import (
    OrderCancelSerializer,
    OrderCreateSerializer,
    OrderRateSerializer,
    OrderRatingSerializer,
    OrderSerializer,
    OrderVerifyDeliverySerializer,
    OrderVerifyPickupSerializer,
)
from apps.orders.services import OrderService
from apps.pricing.models import Quote


class OrderViewSet(viewsets.ModelViewSet):
    """Lifecycle operations for delivery orders."""

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> Any:
        user = self.request.user
        if user.has_any_role("ADMIN", "DISPATCHER"):
            return Order.objects.select_related("customer", "rider__user", "quote").prefetch_related("status_logs").all()
        elif user.has_role("RIDER") and hasattr(user, "rider_profile"):
            return Order.objects.filter(
                Q(customer=user) | Q(rider=user.rider_profile)
            ).select_related("customer", "rider__user", "quote").prefetch_related("status_logs")
        return Order.objects.filter(customer=user).select_related("customer", "rider__user", "quote").prefetch_related("status_logs")

    @extend_schema(request=OrderCreateSerializer, responses={201: OrderSerializer}, tags=["Orders"], summary="Create Order from Quote")
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        quote = get_object_or_404(Quote, pk=data["quote_id"])

        try:
            order = OrderService.create_from_quote(
                quote=quote,
                customer=request.user,
                sender_name=data["sender_name"],
                sender_phone=data["sender_phone"],
                recipient_name=data["recipient_name"],
                recipient_phone=data["recipient_phone"],
                instructions=data.get("instructions", ""),
                pickup_notes=data.get("pickup_notes", ""),
                delivery_notes=data.get("delivery_notes", ""),
                parcel_description=data.get("parcel_description", ""),
                parcel_weight_kg=data.get("parcel_weight_kg", 1.0),
                parcel_type=data.get("parcel_type", "SMALL_BOX"),
                is_fragile=data.get("is_fragile", False),
                requires_signature=data.get("requires_signature", False),
                payment_method=data.get("payment_method", "COD"),
                cod_amount=data.get("cod_amount", 0.0),
            )
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": {"code": "ORDER_CREATION_FAILED", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(tags=["Orders"], summary="Rider Arrived at Pickup")
    @action(detail=True, methods=["post"], url_path="arrived-pickup")
    def arrived_pickup(self, request: Request, pk: str = None) -> Response:
        order = self.get_object()
        try:
            updated = OrderService.transition(order, OrderStatus.RIDER_ARRIVED_PICKUP, changed_by=request.user, note="Rider arrived at pickup point.")
            return Response(OrderSerializer(updated).data)
        except ValueError as e:
            return Response({"error": {"code": "INVALID_TRANSITION", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(request=OrderVerifyPickupSerializer, tags=["Orders"], summary="Verify Pickup OTP")
    @action(detail=True, methods=["post"], url_path="verify-pickup", parser_classes=[MultiPartParser, FormParser])
    def verify_pickup(self, request: Request, pk: str = None) -> Response:
        order = self.get_object()
        code = request.data.get("code", "")
        proof_file = request.FILES.get("proof")
        try:
            updated = OrderService.verify_pickup_otp(order, code, proof_file)
            return Response(OrderSerializer(updated).data)
        except ValueError as e:
            return Response({"error": {"code": "VERIFICATION_FAILED", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(tags=["Orders"], summary="Rider Arrived at Delivery")
    @action(detail=True, methods=["post"], url_path="arrived-delivery")
    def arrived_delivery(self, request: Request, pk: str = None) -> Response:
        order = self.get_object()
        try:
            updated = OrderService.transition(order, OrderStatus.ARRIVED_DELIVERY, changed_by=request.user, note="Rider arrived at destination.")
            return Response(OrderSerializer(updated).data)
        except ValueError as e:
            return Response({"error": {"code": "INVALID_TRANSITION", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(request=OrderVerifyDeliverySerializer, tags=["Orders"], summary="Verify Delivery OTP")
    @action(detail=True, methods=["post"], url_path="verify-delivery", parser_classes=[MultiPartParser, FormParser])
    def verify_delivery(self, request: Request, pk: str = None) -> Response:
        order = self.get_object()
        code = request.data.get("code", "")
        recipient_name = request.data.get("recipient_name", "")
        proof_file = request.FILES.get("proof")
        signature_file = request.FILES.get("signature")
        try:
            updated = OrderService.verify_delivery_otp(
                order=order,
                code=code,
                proof_file=proof_file,
                signature_file=signature_file,
                recipient_name=recipient_name,
            )
            return Response(OrderSerializer(updated).data)
        except ValueError as e:
            return Response({"error": {"code": "VERIFICATION_FAILED", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(request=OrderCancelSerializer, tags=["Orders"], summary="Cancel Order")
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request: Request, pk: str = None) -> Response:
        order = self.get_object()
        serializer = OrderCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = OrderService.cancel_order(order, cancelled_by=request.user, reason=serializer.validated_data["reason"])
            return Response(OrderSerializer(updated).data)
        except ValueError as e:
            return Response({"error": {"code": "CANCELLATION_FAILED", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(request=OrderRateSerializer, responses={201: OrderRatingSerializer}, tags=["Orders"], summary="Rate Completed Order")
    @action(detail=True, methods=["post"], url_path="rate")
    def rate(self, request: Request, pk: str = None) -> Response:
        order = self.get_object()
        serializer = OrderRateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            rating = OrderService.rate_order(
                order=order,
                customer=request.user,
                score=serializer.validated_data["score"],
                comment=serializer.validated_data.get("comment", ""),
                tags=serializer.validated_data.get("tags", ""),
            )
            return Response(OrderRatingSerializer(rating).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": {"code": "RATING_FAILED", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)
