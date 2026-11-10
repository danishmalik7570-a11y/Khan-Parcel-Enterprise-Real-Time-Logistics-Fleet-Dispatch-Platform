# =============================================================================
# Khan Parcel — Tracking URLs
# =============================================================================

from __future__ import annotations

from django.urls import path

from apps.tracking.views import OrderLiveTrackingView

app_name = "tracking"

urlpatterns = [
    path("orders/<uuid:order_id>/", OrderLiveTrackingView.as_view(), name="order-live"),
]
