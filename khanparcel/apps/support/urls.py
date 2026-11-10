# =============================================================================
# Khan Parcel — Support URLs
# =============================================================================

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.support.views import AdminSOSViewSet, SupportTicketViewSet, TriggerSOSView

app_name = "support"

router = DefaultRouter()
router.register(r"tickets", SupportTicketViewSet, basename="ticket")
router.register(r"admin/sos", AdminSOSViewSet, basename="admin-sos")

urlpatterns = [
    path("sos/", TriggerSOSView.as_view(), name="trigger-sos"),
    path("", include(router.urls)),
]
