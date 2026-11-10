# =============================================================================
# Khan Parcel — Riders URLs
# =============================================================================

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.riders.views import (
    AdminDocumentReviewView,
    AdminRiderViewSet,
    RiderDocumentUploadView,
    RiderLocationView,
    RiderOnboardingView,
    RiderProfileView,
    RiderShiftListView,
    RiderStatusToggleView,
)

app_name = "riders"

router = DefaultRouter()
router.register(r"admin/riders", AdminRiderViewSet, basename="admin-rider")

urlpatterns = [
    path("me/", RiderProfileView.as_view(), name="me"),
    path("onboard/", RiderOnboardingView.as_view(), name="onboard"),
    path("documents/upload/", RiderDocumentUploadView.as_view(), name="document-upload"),
    path("status/toggle/", RiderStatusToggleView.as_view(), name="status-toggle"),
    path("location/", RiderLocationView.as_view(), name="location-update"),
    path("shifts/", RiderShiftListView.as_view(), name="shifts"),
    path("admin/documents/<uuid:pk>/review/", AdminDocumentReviewView.as_view(), name="document-review"),
    path("", include(router.urls)),
]
