# =============================================================================
# Khan Parcel — Orders URLs
# =============================================================================

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.orders.views import OrderViewSet

app_name = "orders"

router = DefaultRouter()
router.register(r"", OrderViewSet, basename="order")

urlpatterns = [
    path("", include(router.urls)),
]
