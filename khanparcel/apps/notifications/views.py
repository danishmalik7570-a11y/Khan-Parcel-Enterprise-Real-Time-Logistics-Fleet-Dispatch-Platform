# =============================================================================
# Khan Parcel — Notifications Views
# =============================================================================

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """List authenticated user's notifications."""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> Any:
        return Notification.objects.filter(user=self.request.user).order_by("-sent_at")


class NotificationMarkReadView(APIView):
    """Mark all or specific notifications as read."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: dict}, tags=["Notifications"], summary="Mark Notifications Read")
    def post(self, request: Request, pk: str = None) -> Response:
        if pk:
            Notification.objects.filter(id=pk, user=request.user).update(is_read=True)
        else:
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"status": "ok"})
