# =============================================================================
# Khan Parcel — Pricing Views
# =============================================================================

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdminOrDispatcher, IsStaff
from apps.pricing.models import PriceRule, PromoCode, Quote, SurgeCell
from apps.pricing.serializers import (
    PriceRuleSerializer,
    PromoCodeSerializer,
    PromoValidateSerializer,
    QuoteRequestSerializer,
    QuoteResponseSerializer,
    SurgeCellSerializer,
)
from apps.pricing.services import QuoteService


class QuoteCreateView(APIView):
    """Calculate and return a binding price quote with route polyline."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=QuoteRequestSerializer,
        responses={201: QuoteResponseSerializer},
        tags=["Pricing"],
        summary="Request Delivery Quote",
    )
    def post(self, request: Request) -> Response:
        serializer = QuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user if request.user and request.user.is_authenticated else None

        quote = QuoteService.create_quote(
            pickup_lat=data["pickup_lat"],
            pickup_lng=data["pickup_lng"],
            dropoff_lat=data["dropoff_lat"],
            dropoff_lng=data["dropoff_lng"],
            pickup_address=data["pickup_address"],
            dropoff_address=data["dropoff_address"],
            vehicle_type=data["vehicle_type"],
            user=user,
            promo_code_str=data.get("promo_code"),
            city=data.get("city", "Islamabad"),
        )

        return Response(QuoteResponseSerializer(quote).data, status=status.HTTP_201_CREATED)


class QuoteDetailView(APIView):
    """Retrieve an existing quote by ID."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses={200: QuoteResponseSerializer}, tags=["Pricing"], summary="Get Quote")
    def get(self, request: Request, pk: str) -> Response:
        quote = get_object_or_404(Quote, pk=pk)
        return Response(QuoteResponseSerializer(quote).data)


class PromoValidateView(APIView):
    """Check validity and discount value of a promo code."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(request=PromoValidateSerializer, tags=["Pricing"], summary="Validate Promo Code")
    def post(self, request: Request) -> Response:
        serializer = PromoValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code_str = serializer.validated_data["code"].strip()
        amount = serializer.validated_data["order_amount"]

        promo = PromoCode.objects.filter(code__iexact=code_str).first()
        if not promo:
            return Response(
                {"is_valid": False, "message": "Invalid promo code."},
                status=status.HTTP_404_NOT_FOUND,
            )

        is_valid, reason = promo.is_valid_for_amount(amount)
        if not is_valid:
            return Response(
                {"is_valid": False, "message": reason},
                status=status.HTTP_400_BAD_REQUEST,
            )

        discount = promo.calculate_discount(amount)
        return Response({
            "is_valid": True,
            "code": promo.code,
            "discount_type": promo.discount_type,
            "discount_value": promo.discount_value,
            "calculated_discount": discount,
            "final_amount": max(amount - discount, 0),
        })


class PriceRuleViewSet(viewsets.ModelViewSet):
    """CRUD operations for base pricing tariffs."""

    queryset = PriceRule.objects.all().order_by("city", "vehicle_type")
    serializer_class = PriceRuleSerializer

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsStaff()]


class PromoCodeViewSet(viewsets.ModelViewSet):
    """Admin management for promo vouchers."""

    queryset = PromoCode.objects.all().order_by("-created_at")
    serializer_class = PromoCodeSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaff]


class SurgeCellViewSet(viewsets.ReadOnlyModelViewSet):
    """View active surge cells and heatmaps."""

    queryset = SurgeCell.objects.filter(multiplier__gt=1.00).order_by("-multiplier")
    serializer_class = SurgeCellSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrDispatcher]
