# =============================================================================
# Khan Parcel — Dispatch URLs
# =============================================================================

from __future__ import annotations

from django.urls import path

from apps.dispatch.views import (
    DispatchLogListView,
    ManualAssignView,
    RiderOfferAcceptView,
    RiderOfferListView,
    RiderOfferRejectView,
)

app_name = "dispatch"

urlpatterns = [
    path("offers/", RiderOfferListView.as_view(), name="offers-list"),
    path("offers/<uuid:pk>/accept/", RiderOfferAcceptView.as_view(), name="offer-accept"),
    path("offers/<uuid:pk>/reject/", RiderOfferRejectView.as_view(), name="offer-reject"),
    path("manual-assign/", ManualAssignView.as_view(), name="manual-assign"),
    path("logs/", DispatchLogListView.as_view(), name="dispatch-logs"),
]
