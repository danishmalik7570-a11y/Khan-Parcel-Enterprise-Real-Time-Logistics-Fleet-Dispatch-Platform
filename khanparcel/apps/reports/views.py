# =============================================================================
# Khan Parcel — Reports & Operations Views
# =============================================================================

from __future__ import annotations

import csv
from decimal import Decimal
from typing import Any

from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdminOrDispatcher
from apps.orders.models import Order, OrderStatus
from apps.payments.models import LedgerEntry
from apps.pricing.models import SurgeCell
from apps.riders.models import RiderProfile, RiderStatus
from apps.support.models import SOSAlert


class DashboardStatsView(APIView):
    """Real-time operations metrics for dispatcher and management control room."""

    permission_classes = [permissions.IsAuthenticated, IsAdminOrDispatcher]

    @extend_schema(responses={200: dict}, tags=["Ops"], summary="Dashboard Overview Metrics")
    def get(self, request: Request) -> Response:
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # 1. Orders
        active_statuses = [
            OrderStatus.CREATED,
            OrderStatus.SEARCHING_RIDER,
            OrderStatus.RIDER_ASSIGNED,
            OrderStatus.RIDER_ARRIVED_PICKUP,
            OrderStatus.PICKED_UP,
            OrderStatus.ARRIVED_DELIVERY,
        ]
        active_orders_count = Order.objects.filter(status__in=active_statuses).count()
        today_orders = Order.objects.filter(created_at__gte=today_start)
        today_total = today_orders.count()
        today_delivered = today_orders.filter(status=OrderStatus.DELIVERED).count()
        today_cancelled = today_orders.filter(status=OrderStatus.CANCELLED).count()

        completion_rate = (
            round((today_delivered / today_total) * 100, 1)
            if today_total > 0
            else 100.0
        )

        today_gmv = today_orders.filter(status=OrderStatus.DELIVERED).aggregate(
            gmv=Sum("total_amount")
        )["gmv"] or Decimal("0.00")

        # 2. Fleet
        online_riders = RiderProfile.objects.filter(is_online=True)
        online_count = online_riders.count()
        available_count = online_riders.filter(status=RiderStatus.AVAILABLE).count()
        busy_count = online_riders.filter(status=RiderStatus.BUSY).count()

        # 3. Emergency SOS
        active_sos_count = SOSAlert.objects.filter(resolved_at__isnull=True).count()

        # 4. Surge
        active_surge_cells = SurgeCell.objects.filter(multiplier__gt=1.00).count()

        return Response({
            "active_orders": active_orders_count,
            "today_total_orders": today_total,
            "today_delivered_orders": today_delivered,
            "today_cancelled_orders": today_cancelled,
            "completion_rate_pct": completion_rate,
            "today_gmv_pkr": str(today_gmv),
            "fleet": {
                "total_online": online_count,
                "available": available_count,
                "busy": busy_count,
            },
            "active_sos_alerts": active_sos_count,
            "active_surge_hexagons": active_surge_cells,
            "timestamp": timezone.now().isoformat(),
        })


class FleetLiveView(APIView):
    """Real-time locations of all active riders for the live dispatch map."""

    permission_classes = [permissions.IsAuthenticated, IsAdminOrDispatcher]

    @extend_schema(responses={200: list}, tags=["Ops"], summary="Live Fleet Positions")
    def get(self, request: Request) -> Response:
        riders = RiderProfile.objects.filter(
            is_online=True,
            current_location__isnull=False,
        ).select_related("user")

        data = []
        for r in riders:
            data.append({
                "id": str(r.id),
                "name": r.user.name or str(r.user.phone),
                "phone": str(r.user.phone),
                "lat": r.current_location.y,
                "lng": r.current_location.x,
                "heading": r.heading,
                "speed": r.speed,
                "battery": r.battery_level,
                "status": r.status,
                "active_orders": r.active_orders_count,
                "rating": str(r.rating_avg),
                "last_heartbeat": r.last_heartbeat_at.isoformat() if r.last_heartbeat_at else None,
            })

        return Response(data)


class ExportOrdersCSVView(APIView):
    """Download orders report in CSV format."""

    permission_classes = [permissions.IsAuthenticated, IsAdminOrDispatcher]

    @extend_schema(tags=["Ops"], summary="Export Orders CSV")
    def get(self, request: Request) -> HttpResponse:
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="khanparcel_orders.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "Order Number",
            "Customer",
            "Customer Phone",
            "Rider",
            "Status",
            "Vehicle",
            "Fare (PKR)",
            "COD (PKR)",
            "Total (PKR)",
            "Payment Method",
            "Payment Status",
            "Pickup Address",
            "Dropoff Address",
            "Created At",
            "Delivered At",
        ])

        orders = Order.objects.select_related("customer", "rider__user").order_by("-created_at")[:5000]
        for o in orders:
            writer.writerow([
                o.order_number,
                o.customer.name,
                str(o.customer.phone),
                o.rider.user.name if o.rider else "",
                o.status,
                o.vehicle_type,
                str(o.fare_amount),
                str(o.cod_amount),
                str(o.total_amount),
                o.payment_method,
                o.payment_status,
                o.pickup_address,
                o.dropoff_address,
                o.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                o.delivered_at.strftime("%Y-%m-%d %H:%M:%S") if o.delivered_at else "",
            ])

        return response


class ExportFinancialCSVView(APIView):
    """Download double-entry ledger transactions in CSV format."""

    permission_classes = [permissions.IsAuthenticated, IsAdminOrDispatcher]

    @extend_schema(tags=["Ops"], summary="Export Financial Ledger CSV")
    def get(self, request: Request) -> HttpResponse:
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="khanparcel_ledger.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "Transaction ID",
            "Order Number",
            "Account Type",
            "Type",
            "Amount (PKR)",
            "Balance After (PKR)",
            "Description",
            "Timestamp",
        ])

        entries = LedgerEntry.objects.select_related("order").order_by("-created_at")[:5000]
        for e in entries:
            writer.writerow([
                str(e.transaction_id),
                e.order.order_number if e.order else "",
                e.account_type,
                e.entry_type,
                str(e.amount),
                str(e.balance_after),
                e.description,
                e.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ])

        return response
