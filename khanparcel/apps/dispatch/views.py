# =============================================================================
# Khan Parcel — Dispatch Views
# =============================================================================

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdminOrDispatcher
from apps.dispatch.models import DispatchLog, DispatchOffer, DispatchOfferStatus
from apps.dispatch.serializers import (
    DispatchLogSerializer,
    DispatchOfferRejectSerializer,
    DispatchOfferSerializer,
    ManualAssignSerializer,
)
from apps.dispatch.services import DispatchEngine
from apps.orders.serializers import OrderSerializer
from apps.riders.models import RiderProfile


class RiderOfferListView(generics.ListAPIView):
    """List active dispatch offers for the authenticated rider."""

    serializer_class = DispatchOfferSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> Any:
        profile = get_object_or_404(RiderProfile, user=self.request.user)
        return DispatchOffer.objects.filter(
            rider=profile,
            status=DispatchOfferStatus.PENDING,
        ).select_related("order", "order__customer").order_by("-created_at")


class RiderOfferAcceptView(APIView):
    """Rider accepts an open delivery job offer."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: OrderSerializer}, tags=["Dispatch"], summary="Accept Job Offer")
    def post(self, request: Request, pk: str) -> Response:
        profile = get_object_or_404(RiderProfile, user=request.user)
        try:
            order = DispatchEngine.accept_offer(offer_id=pk, rider=profile)
            return Response(OrderSerializer(order).data)
        except ValueError as e:
            return Response({"error": {"code": "OFFER_ACCEPT_FAILED", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)


class RiderOfferRejectView(APIView):
    """Rider rejects an open delivery job offer."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=DispatchOfferRejectSerializer, responses={200: dict}, tags=["Dispatch"], summary="Reject Job Offer")
    def post(self, request: Request, pk: str) -> Response:
        profile = get_object_or_404(RiderProfile, user=request.user)
        serializer = DispatchOfferRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        DispatchEngine.reject_offer(
            offer_id=pk,
            rider=profile,
            reason=serializer.validated_data.get("reason", ""),
        )
        return Response({"status": "rejected"})


class ManualAssignView(APIView):
    """Dispatcher manual override to assign a rider to an order."""

    permission_classes = [permissions.IsAuthenticated, IsAdminOrDispatcher]

    @extend_schema(request=ManualAssignSerializer, responses={200: OrderSerializer}, tags=["Dispatch"], summary="Manual Rider Assignment")
    def post(self, request: Request) -> Response:
        serializer = ManualAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = DispatchEngine.manual_assign(
                order_id=str(serializer.validated_data["order_id"]),
                rider_id=str(serializer.validated_data["rider_id"]),
                dispatcher=request.user,
            )
            return Response(OrderSerializer(order).data)
        except ValueError as e:
            return Response({"error": {"code": "MANUAL_ASSIGN_FAILED", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)


class DispatchLogListView(generics.ListAPIView):
    """List dispatch audit logs for order diagnostics."""

    serializer_class = DispatchLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrDispatcher]

    def get_queryset(self) -> Any:
        order_id = self.request.query_params.get("order_id")
        qs = DispatchLog.objects.select_related("order").order_by("-created_at")
        if order_id:
            qs = qs.filter(order_id=order_id)
        return qs[:100]
