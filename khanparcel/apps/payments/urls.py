# =============================================================================
# Khan Parcel — Payments URLs
# =============================================================================

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.payments.views import (
    AdminCODRemittanceViewSet,
    AdminPayoutViewSet,
    CODRemittanceListView,
    LedgerListView,
    PayoutRequestListView,
    WalletDetailView,
    WalletTopupView,
)

app_name = "payments"

router = DefaultRouter()
router.register(r"admin/payouts", AdminPayoutViewSet, basename="admin-payout")
router.register(r"admin/cod", AdminCODRemittanceViewSet, basename="admin-cod")

urlpatterns = [
    path("wallet/", WalletDetailView.as_view(), name="wallet-detail"),
    path("wallet/topup/", WalletTopupView.as_view(), name="wallet-topup"),
    path("wallet/statement/", LedgerListView.as_view(), name="wallet-statement"),
    path("payouts/", PayoutRequestListView.as_view(), name="payout-requests"),
    path("cod/remit/", CODRemittanceListView.as_view(), name="cod-remittance"),
    path("", include(router.urls)),
]
