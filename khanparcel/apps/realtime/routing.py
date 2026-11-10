# =============================================================================
# Khan Parcel — Realtime WebSocket Routing
# =============================================================================

from __future__ import annotations

from django.urls import path

from apps.realtime.consumers import (
    ChatConsumer,
    DispatcherConsumer,
    PublicTrackingConsumer,
    RiderConsumer,
    TrackingConsumer,
)

websocket_urlpatterns = [
    path("ws/tracking/<uuid:order_id>/", TrackingConsumer.as_asgi(), name="ws-tracking"),
    path("ws/public/tracking/<str:token>/", PublicTrackingConsumer.as_asgi(), name="ws-public-tracking"),
    path("ws/dispatcher/", DispatcherConsumer.as_asgi(), name="ws-dispatcher"),
    path("ws/rider/", RiderConsumer.as_asgi(), name="ws-rider"),
    path("ws/chat/<uuid:order_id>/", ChatConsumer.as_asgi(), name="ws-chat"),
]
