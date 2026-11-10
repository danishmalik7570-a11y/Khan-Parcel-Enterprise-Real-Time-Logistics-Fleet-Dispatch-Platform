# =============================================================================
# Khan Parcel — Payments Views
# =============================================================================

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdminOrDispatcher, IsStaff
from apps.payments.models import CODRemittance, LedgerEntry, PayoutRequest, Wallet
from apps.payments.serializers import (
    CODRemittanceSerializer,
    CODRemittanceSubmitSerializer,
    CODRemittanceVerifySerializer,
    LedgerEntrySerializer,
    PayoutCreateSerializer,
    PayoutProcessSerializer,
    PayoutRequestSerializer,
    WalletSerializer,
    WalletTopupSerializer,
)
from apps.payments.services import PaymentService
from apps.riders.models import RiderProfile


class WalletDetailView(APIView):
    """Retrieve the current user's digital wallet and balance."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: WalletSerializer}, tags=["Payments"], summary="My Wallet")
    def get(self, request: Request) -> Response:
        wallet = PaymentService.get_or_create_wallet(request.user)
        return Response(WalletSerializer(wallet).data)


class WalletTopupView(APIView):
    """Top up wallet balance via payment gateway / credit card."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=WalletTopupSerializer, responses={200: WalletSerializer}, tags=["Payments"], summary="Topup Wallet")
    def post(self, request: Request) -> Response:
        serializer = WalletTopupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            wallet = PaymentService.topup_wallet(
                user=request.user,
                amount=serializer.validated_data["amount"],
                payment_method=serializer.validated_data["payment_method"],
                reference=serializer.validated_data.get("reference", ""),
            )
            return Response(WalletSerializer(wallet).data)
        except ValueError as e:
            return Response({"error": {"code": "TOPUP_FAILED", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)


class LedgerListView(generics.ListAPIView):
    """Audit statement of financial transactions on the user's wallet."""

    serializer_class = LedgerEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> Any:
        wallet = PaymentService.get_or_create_wallet(self.request.user)
        return LedgerEntry.objects.filter(wallet=wallet).order_by("-created_at")


class PayoutRequestListView(generics.ListCreateAPIView):
    """Rider endpoint to list previous payouts and request a new withdrawal."""

    serializer_class = PayoutRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> Any:
        profile = get_object_or_404(RiderProfile, user=self.request.user)
        return PayoutRequest.objects.filter(rider=profile).order_by("-created_at")

    @extend_schema(request=PayoutCreateSerializer, responses={201: PayoutRequestSerializer}, tags=["Payments"], summary="Request Payout")
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = PayoutCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = get_object_or_404(RiderProfile, user=request.user)

        try:
            req = PaymentService.request_payout(
                rider=profile,
                amount=serializer.validated_data["amount"],
                payout_method=serializer.validated_data["payout_method"],
                account_title=serializer.validated_data["account_title"],
                account_number=serializer.validated_data["account_number"],
                bank_name=serializer.validated_data.get("bank_name", ""),
            )
            return Response(PayoutRequestSerializer(req).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": {"code": "PAYOUT_REQUEST_FAILED", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)


class CODRemittanceListView(generics.ListCreateAPIView):
    """Rider endpoint to submit bank deposit slips for collected COD cash."""

    serializer_class = CODRemittanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self) -> Any:
        profile = get_object_or_404(RiderProfile, user=self.request.user)
        return CODRemittance.objects.filter(rider=profile).order_by("-created_at")

    @extend_schema(
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "slip": {"type": "string", "format": "binary"},
                    "bank_reference": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["amount", "slip"],
            }
        },
        responses={201: CODRemittanceSerializer},
        tags=["Payments"],
        summary="Submit COD Deposit Slip",
    )
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = CODRemittanceSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = get_object_or_404(RiderProfile, user=request.user)
        slip_file = request.FILES.get("slip")

        if not slip_file:
            return Response({"error": {"code": "MISSING_SLIP", "message": "Deposit slip image is required."}}, status=status.HTTP_400_BAD_REQUEST)

        rem = PaymentService.submit_cod_remittance(
            rider=profile,
            amount=serializer.validated_data["amount"],
            slip_image=slip_file,
            bank_ref=serializer.validated_data.get("bank_reference", ""),
            notes=serializer.validated_data.get("notes", ""),
        )
        return Response(CODRemittanceSerializer(rem).data, status=status.HTTP_201_CREATED)


# ─── Admin Endpoints ──────────────────────────────────────────────────────────

class AdminPayoutViewSet(viewsets.ModelViewSet):
    """Staff review and processing of rider withdrawal requests."""

    serializer_class = PayoutRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaff]
    queryset = PayoutRequest.objects.select_related("rider__user", "reviewed_by").all().order_by("-created_at")

    @extend_schema(request=PayoutProcessSerializer, tags=["Payments"], summary="Process Payout")
    @action(detail=True, methods=["post"], url_path="process")
    def process_payout(self, request: Request, pk: str = None) -> Response:
        serializer = PayoutProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            req = PaymentService.process_payout(
                payout_id=pk,
                admin_user=request.user,
                approve=serializer.validated_data["approve"],
                reference_number=serializer.validated_data.get("reference_number", ""),
                rejection_reason=serializer.validated_data.get("rejection_reason", ""),
            )
            return Response(PayoutRequestSerializer(req).data)
        except ValueError as e:
            return Response({"error": {"code": "PAYOUT_PROCESS_FAILED", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)


class AdminCODRemittanceViewSet(viewsets.ModelViewSet):
    """Staff verification of rider cash remittance deposits."""

    serializer_class = CODRemittanceSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaff]
    queryset = CODRemittance.objects.select_related("rider__user", "verified_by").all().order_by("-created_at")

    @extend_schema(request=CODRemittanceVerifySerializer, tags=["Payments"], summary="Verify COD Remittance")
    @action(detail=True, methods=["post"], url_path="verify")
    def verify_remittance(self, request: Request, pk: str = None) -> Response:
        serializer = CODRemittanceVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            rem = PaymentService.verify_cod_remittance(
                remittance_id=pk,
                admin_user=request.user,
                approve=serializer.validated_data["approve"],
            )
            return Response(CODRemittanceSerializer(rem).data)
        except ValueError as e:
            return Response({"error": {"code": "VERIFY_FAILED", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)
