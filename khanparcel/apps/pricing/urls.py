# =============================================================================
# Khan Parcel — Pricing URLs
# =============================================================================

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.pricing.views import (
    PriceRuleViewSet,
    PromoCodeViewSet,
    PromoValidateView,
    QuoteCreateView,
    QuoteDetailView,
    SurgeCellViewSet,
)

app_name = "pricing"

router = DefaultRouter()
router.register(r"rules", PriceRuleViewSet, basename="price-rule")
router.register(r"promos", PromoCodeViewSet, basename="promo-code")
router.register(r"surge/cells", SurgeCellViewSet, basename="surge-cell")

urlpatterns = [
    path("quote/", QuoteCreateView.as_view(), name="quote-create"),
    path("quote/<uuid:pk>/", QuoteDetailView.as_view(), name="quote-detail"),
    path("promo/validate/", PromoValidateView.as_view(), name="promo-validate"),
    path("", include(router.urls)),
]
