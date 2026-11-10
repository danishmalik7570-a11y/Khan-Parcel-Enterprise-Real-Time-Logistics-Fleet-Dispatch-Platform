# =============================================================================
# Khan Parcel — Business URLs
# =============================================================================

from __future__ import annotations

from django.urls import path

from apps.business.views import (
    BulkBatchListView,
    BulkOrderUploadView,
    BusinessProfileView,
)

app_name = "business"

urlpatterns = [
    path("profile/", BusinessProfileView.as_view(), name="profile"),
    path("bulk/upload/", BulkOrderUploadView.as_view(), name="bulk-upload"),
    path("bulk/batches/", BulkBatchListView.as_view(), name="bulk-batches"),
]
