# =============================================================================
# Khan Parcel — Support Views
# =============================================================================

from __future__ import annotations

from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from apps.core.gis_compat import Point
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdminOrDispatcher, IsStaff
from apps.riders.models import RiderProfile
from apps.support.models import SOSAlert, SupportTicket, TicketMessage, TicketStatus
from apps.support.serializers import (
    SOSAlertSerializer,
    SOSCreateSerializer,
    SupportTicketCreateSerializer,
    SupportTicketSerializer,
    TicketMessageSerializer,
)


class SupportTicketViewSet(viewsets.ModelViewSet):
    """User support ticket management."""

    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> Any:
        user = self.request.user
        if user.has_any_role("ADMIN", "SUPPORT"):
            return SupportTicket.objects.select_related("user", "assigned_to", "order").prefetch_related("messages").all()
        return SupportTicket.objects.filter(user=user).select_related("user", "assigned_to", "order").prefetch_related("messages")

    def perform_create(self, serializer: Any) -> None:
        serializer.save(user=self.request.user)

    @extend_schema(request=TicketMessageSerializer, tags=["Support"], summary="Add Message to Ticket")
    @action(detail=True, methods=["post"], url_path="messages")
    def add_message(self, request: Request, pk: str = None) -> Response:
        ticket = self.get_object()
        msg_text = request.data.get("message", "").strip()
        if not msg_text:
            return Response({"error": "Message text is required."}, status=status.HTTP_400_BAD_REQUEST)

        msg = TicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            message=msg_text,
            attachment=request.FILES.get("attachment"),
        )
        return Response(TicketMessageSerializer(msg).data, status=status.HTTP_201_CREATED)

    @extend_schema(tags=["Support"], summary="Resolve Support Ticket")
    @action(detail=True, methods=["post"], url_path="resolve", permission_classes=[permissions.IsAuthenticated, IsStaff])
    def resolve(self, request: Request, pk: str = None) -> Response:
        ticket = self.get_object()
        ticket.status = TicketStatus.RESOLVED
        ticket.assigned_to = request.user
        ticket.save(update_fields=["status", "assigned_to", "updated_at"])
        return Response(SupportTicketSerializer(ticket).data)


class TriggerSOSView(APIView):
    """Rider triggers instant emergency SOS alert."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=SOSCreateSerializer, responses={201: SOSAlertSerializer}, tags=["Support"], summary="Trigger SOS")
    def post(self, request: Request) -> Response:
        profile = get_object_or_404(RiderProfile, user=request.user)
        serializer = SOSCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        loc = None
        if data.get("lat") is not None and data.get("lng") is not None:
            loc = Point(data["lng"], data["lat"], srid=4326)
        elif profile.current_location:
            loc = profile.current_location

        sos = SOSAlert.objects.create(
            rider=profile,
            order_id=data.get("order_id"),
            location=loc,
            reason=data.get("reason", "Accident or Security Incident"),
        )

        # Broadcast critical alert to all dispatchers
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    "dispatchers",
                    {
                        "type": "sos_alert",
                        "sos_id": str(sos.id),
                        "rider_id": str(profile.id),
                        "rider_name": profile.user.name,
                        "rider_phone": str(profile.user.phone),
                        "lat": loc.y if loc else None,
                        "lng": loc.x if loc else None,
                        "reason": sos.reason,
                        "created_at": sos.created_at.isoformat(),
                    },
                )
        except Exception:
            pass

        return Response(SOSAlertSerializer(sos).data, status=status.HTTP_201_CREATED)


class AdminSOSViewSet(viewsets.ModelViewSet):
    """Dispatcher monitoring and resolution of emergency SOS signals."""

    serializer_class = SOSAlertSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrDispatcher]
    queryset = SOSAlert.objects.select_related("rider__user", "order").all().order_by("-created_at")

    @extend_schema(tags=["Support"], summary="Resolve SOS Alert")
    @action(detail=True, methods=["post"], url_path="resolve")
    def resolve_sos(self, request: Request, pk: str = None) -> Response:
        sos = self.get_object()
        sos.resolved_at = timezone.now()
        sos.resolved_by = request.user
        sos.save(update_fields=["resolved_at", "resolved_by", "updated_at"])
        return Response(SOSAlertSerializer(sos).data)
