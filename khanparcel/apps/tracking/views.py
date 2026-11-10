# =============================================================================
# Khan Parcel — Tracking Views
# =============================================================================

from __future__ import annotations

from typing import Any

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer


class OrderLiveTrackingView(APIView):
    """Retrieve full live tracking details for an authenticated user's order."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: dict}, tags=["Tracking"], summary="Live Order Tracking")
    def get(self, request: Request, order_id: str) -> Response:
        order = get_object_or_404(
            Order.objects.select_related("rider__user", "quote", "customer"),
            id=order_id,
        )

        # Access check
        if not (request.user == order.customer or (order.rider and request.user == order.rider.user) or request.user.has_any_role("ADMIN", "DISPATCHER")):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        rider_data = None
        if order.rider:
            rider = order.rider
            rider_data = {
                "id": str(rider.id),
                "name": rider.user.name,
                "phone": str(rider.user.phone),
                "rating": str(rider.rating_avg),
                "lat": rider.current_location.y if rider.current_location else None,
                "lng": rider.current_location.x if rider.current_location else None,
                "heading": rider.heading,
                "speed": rider.speed,
                "battery": rider.battery_level,
                "last_seen": rider.last_heartbeat_at.isoformat() if rider.last_heartbeat_at else None,
            }

        return Response({
            "order": OrderSerializer(order).data,
            "rider": rider_data,
            "route_polyline": order.quote.route_polyline if order.quote else "",
            "ws_url": f"/ws/tracking/{order.id}/",
        })


class PublicTrackingAPIView(APIView):
    """Public JSON endpoint for recipient tracking via shareable web link."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses={200: dict}, tags=["Tracking"], summary="Public Tracking JSON")
    def get(self, request: Request, token: str) -> Response:
        order = get_object_or_404(
            Order.objects.select_related("rider__user", "quote"),
            public_tracking_token=token,
        )

        rider_loc = None
        if order.rider and order.rider.current_location:
            rider_loc = {
                "lat": order.rider.current_location.y,
                "lng": order.rider.current_location.x,
                "heading": order.rider.heading,
                "name": order.rider.user.name,
                "rating": str(order.rider.rating_avg),
            }

        return Response({
            "order_number": order.order_number,
            "status": order.status,
            "recipient_name": order.recipient_name,
            "pickup_address": order.pickup_address,
            "dropoff_address": order.dropoff_address,
            "pickup_lat": order.pickup_point.y,
            "pickup_lng": order.pickup_point.x,
            "dropoff_lat": order.dropoff_point.y,
            "dropoff_lng": order.dropoff_point.x,
            "rider": rider_loc,
            "route_polyline": order.quote.route_polyline if order.quote else "",
            "created_at": order.created_at.isoformat(),
            "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        })


class PublicTrackingPageView(APIView):
    """Live HTML Leaflet map page for public tracking token link."""

    permission_classes = [permissions.AllowAny]

    def get(self, request: Request, token: str) -> HttpResponse:
        order = get_object_or_404(Order.objects.select_related("rider__user", "quote"), public_tracking_token=token)

        rider_lat = order.rider.current_location.y if (order.rider and order.rider.current_location) else "null"
        rider_lng = order.rider.current_location.x if (order.rider and order.rider.current_location) else "null"
        polyline_str = order.quote.route_polyline if order.quote else ""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Khan Parcel — Live Tracking ({order.order_number})</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://unpkg.com/@mapbox/polyline@1.2.0/src/polyline.js"></script>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    body {{ background: #0f172a; color: #f8fafc; height: 100vh; display: flex; flex-direction: column; }}
    header {{ background: #1e293b; padding: 1rem 1.5rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; }}
    .badge {{ background: #0284c7; color: white; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; }}
    #map {{ flex: 1; width: 100%; }}
    .info-card {{ background: #1e293b; padding: 1.25rem; border-top: 1px solid #334155; }}
    .status-row {{ display: flex; justify-content: space-between; margin-bottom: 0.75rem; }}
    .address {{ color: #94a3b8; font-size: 0.875rem; margin-top: 0.25rem; }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1 style="font-size: 1.25rem; font-weight: 700; color: #38bdf8;">Khan Parcel</h1>
      <p style="color: #94a3b8; font-size: 0.875rem;">Order: {order.order_number}</p>
    </div>
    <span class="badge" id="order-status">{order.status.replace('_', ' ')}</span>
  </header>

  <div id="map"></div>

  <div class="info-card">
    <div class="status-row">
      <div>
        <div style="font-weight: 600;">Recipient: {order.recipient_name}</div>
        <div class="address">Dropoff: {order.dropoff_address}</div>
      </div>
      <div id="rider-info" style="text-align: right;">
        <div style="font-weight: 600;">{order.rider.user.name if order.rider else 'Assigning rider...'}</div>
        <div style="color: #38bdf8; font-size: 0.875rem;">⭐ {order.rider.rating_avg if order.rider else '5.0'}</div>
      </div>
    </div>
  </div>

  <script>
    const pickupLat = {order.pickup_point.y};
    const pickupLng = {order.pickup_point.x};
    const dropLat = {order.dropoff_point.y};
    const dropLng = {order.dropoff_point.x};
    let initialRiderLat = {rider_lat};
    let initialRiderLng = {rider_lng};
    const polylineEncoded = "{polyline_str}";

    const map = L.map('map').setView([pickupLat, pickupLng], 14);
    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
      attribution: '&copy; CartoDB &copy; OpenStreetMap'
    }}).addTo(map);

    L.marker([pickupLat, pickupLng]).addTo(map).bindPopup("<b>Pickup:</b> {order.pickup_address}");
    L.marker([dropLat, dropLng]).addTo(map).bindPopup("<b>Dropoff:</b> {order.dropoff_address}");

    let riderMarker = null;
    if (initialRiderLat !== null && initialRiderLng !== null) {{
      riderMarker = L.marker([initialRiderLat, initialRiderLng]).addTo(map).bindPopup("<b>Rider</b>");
    }}

    if (polylineEncoded) {{
      try {{
        const decoded = polyline.decode(polylineEncoded);
        const polylineLayer = L.polyline(decoded, {{ color: '#0284c7', weight: 4, opacity: 0.8 }}).addTo(map);
        map.fitBounds(polylineLayer.getBounds(), {{ padding: [40, 40] }});
      }} catch (e) {{
        console.error("Polyline render failed", e);
      }}
    }}

    // Realtime WebSocket Connection
    const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${{wsScheme}}://${{window.location.host}}/ws/public/tracking/{token}/`;
    const socket = new WebSocket(wsUrl);

    socket.onmessage = function(event) {{
      const data = JSON.parse(event.data);
      if (data.type === 'rider_location_update') {{
        const lat = data.lat;
        const lng = data.lng;
        if (riderMarker) {{
          riderMarker.setLatLng([lat, lng]);
        }} else {{
          riderMarker = L.marker([lat, lng]).addTo(map).bindPopup("<b>Rider</b>");
        }}
      }} else if (data.type === 'order_update') {{
        document.getElementById('order-status').innerText = data.status.replace('_', ' ');
      }}
    }};
  </script>
</body>
</html>
"""
        return HttpResponse(html, content_type="text/html")
