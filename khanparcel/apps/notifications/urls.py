# =============================================================================
# Khan Parcel — Notifications URLs
# =============================================================================

from __future__ import annotations

from django.urls import path

from apps.notifications.views import NotificationListView, NotificationMarkReadView

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="list"),
    path("read-all/", NotificationMarkReadView.as_view(), name="mark-read-all"),
    path("<uuid:pk>/read/", NotificationMarkReadView.as_view(), name="mark-read"),
]
