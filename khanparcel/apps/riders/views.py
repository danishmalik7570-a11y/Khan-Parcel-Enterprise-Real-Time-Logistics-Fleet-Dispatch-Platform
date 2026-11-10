# =============================================================================
# Khan Parcel — Riders Views
# =============================================================================

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdminOrDispatcher, IsStaff
from apps.riders.models import RiderDocument, RiderProfile, RiderShift
from apps.riders.serializers import (
    DocumentReviewSerializer,
    RiderDocumentSerializer,
    RiderLocationUpdateSerializer,
    RiderOnboardingSerializer,
    RiderProfileSerializer,
    RiderShiftSerializer,
    RiderStatusToggleSerializer,
    VehicleSerializer,
)
from apps.riders.services import RiderService


class RiderProfileView(APIView):
    """Get the current authenticated user's rider profile."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: RiderProfileSerializer}, tags=["Riders"], summary="My Rider Profile")
    def get(self, request: Request) -> Response:
        profile = get_object_or_404(RiderProfile, user=request.user)
        return Response(RiderProfileSerializer(profile).data)


class RiderOnboardingView(APIView):
    """Submit initial KYC onboarding information and vehicle details."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=RiderOnboardingSerializer, responses={201: RiderProfileSerializer}, tags=["Riders"], summary="Onboard Rider")
    def post(self, request: Request) -> Response:
        serializer = RiderOnboardingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = RiderService.submit_onboarding(request.user, serializer.validated_data)
        return Response(RiderProfileSerializer(profile).data, status=status.HTTP_201_CREATED)


class RiderDocumentUploadView(APIView):
    """Upload a KYC verification document."""

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "document_type": {"type": "string"},
                    "file": {"type": "string", "format": "binary"},
                },
                "required": ["document_type", "file"],
            }
        },
        responses={201: RiderDocumentSerializer},
        tags=["Riders"],
        summary="Upload Document",
    )
    def post(self, request: Request) -> Response:
        doc_type = request.data.get("document_type")
        file_obj = request.FILES.get("file")
        if not doc_type or not file_obj:
            return Response(
                {"error": {"code": "MISSING_DATA", "message": "document_type and file are required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = get_object_or_404(RiderProfile, user=request.user)
        doc = RiderService.upload_document(profile, doc_type, file_obj)
        return Response(RiderDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


class RiderStatusToggleView(APIView):
    """Toggle online/offline status."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=RiderStatusToggleSerializer, responses={200: RiderProfileSerializer}, tags=["Riders"], summary="Toggle Online/Offline")
    def post(self, request: Request) -> Response:
        serializer = RiderStatusToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = get_object_or_404(RiderProfile, user=request.user)

        try:
            profile = RiderService.toggle_online(profile, serializer.validated_data["is_online"])
            return Response(RiderProfileSerializer(profile).data)
        except ValueError as e:
            return Response({"error": {"code": "CANNOT_GO_ONLINE", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)


class RiderLocationView(APIView):
    """Send GPS telemetry heartbeat."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=RiderLocationUpdateSerializer, responses={200: dict}, tags=["Riders"], summary="Update Location Telemetry")
    def post(self, request: Request) -> Response:
        serializer = RiderLocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = get_object_or_404(RiderProfile, user=request.user)

        RiderService.update_location(
            profile=profile,
            lat=serializer.validated_data["lat"],
            lng=serializer.validated_data["lng"],
            heading=serializer.validated_data.get("heading"),
            speed=serializer.validated_data.get("speed"),
            battery_level=serializer.validated_data.get("battery_level"),
        )
        return Response({"status": "ok"})


class RiderShiftListView(generics.ListAPIView):
    """List shift history for the authenticated rider."""

    serializer_class = RiderShiftSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> Any:
        profile = get_object_or_404(RiderProfile, user=self.request.user)
        return RiderShift.objects.filter(rider=profile).order_by("-started_at")


# ─── Admin / Dispatcher Operations ───────────────────────────────────────────

class AdminRiderViewSet(viewsets.ModelViewSet):
    """Admin CRUD and dispatch management for riders."""

    serializer_class = RiderProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrDispatcher]
    queryset = RiderProfile.objects.select_related("user").prefetch_related("vehicles", "documents").all()
    filterset_fields = ["status", "review_status", "is_online"]
    search_fields = ["user__name", "user__phone", "cnic_number", "vehicles__plate_number"]


class AdminDocumentReviewView(APIView):
    """Admin endpoint to approve or reject a rider KYC document."""

    permission_classes = [permissions.IsAuthenticated, IsStaff]

    @extend_schema(request=DocumentReviewSerializer, responses={200: RiderDocumentSerializer}, tags=["Riders"], summary="Review Rider Document")
    def post(self, request: Request, pk: str) -> Response:
        serializer = DocumentReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        doc = RiderService.review_document(
            document_id=pk,
            admin_user=request.user,
            status=serializer.validated_data["status"],
            rejection_reason=serializer.validated_data.get("rejection_reason", ""),
        )
        return Response(RiderDocumentSerializer(doc).data)
