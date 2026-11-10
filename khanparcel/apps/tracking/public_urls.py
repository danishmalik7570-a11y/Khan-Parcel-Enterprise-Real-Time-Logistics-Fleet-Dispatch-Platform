# =============================================================================
# Khan Parcel — Public Tracking URLs
# =============================================================================

from __future__ import annotations

from django.urls import path

from apps.tracking.views import PublicTrackingAPIView, PublicTrackingPageView

app_name = "public_tracking"

urlpatterns = [
    path("<str:token>/", PublicTrackingPageView.as_view(), name="page"),
    path("<str:token>/api/", PublicTrackingAPIView.as_view(), name="api"),
]
