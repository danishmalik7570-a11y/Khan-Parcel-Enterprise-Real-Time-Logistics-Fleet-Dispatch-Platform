# =============================================================================
# Khan Parcel — Reports URLs
# =============================================================================

from __future__ import annotations

from django.urls import path

from apps.reports.views import (
    DashboardStatsView,
    ExportFinancialCSVView,
    ExportOrdersCSVView,
    FleetLiveView,
)

app_name = "reports"

urlpatterns = [
    path("dashboard/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("fleet/live/", FleetLiveView.as_view(), name="fleet-live"),
    path("export/orders/", ExportOrdersCSVView.as_view(), name="export-orders"),
    path("export/ledger/", ExportFinancialCSVView.as_view(), name="export-ledger"),
]
