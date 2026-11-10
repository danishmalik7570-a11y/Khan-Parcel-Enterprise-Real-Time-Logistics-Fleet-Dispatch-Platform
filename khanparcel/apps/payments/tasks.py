# =============================================================================
# Khan Parcel — Payments Celery Tasks
# =============================================================================

from __future__ import annotations

from decimal import Decimal

import structlog
from celery import shared_task
from django.db.models import Sum
from django.utils import timezone

from apps.orders.models import Order, PaymentMethod, PaymentStatus
from apps.payments.models import CODRemittance, CODStatus

logger = structlog.get_logger(__name__)


@shared_task(name="apps.payments.tasks.generate_daily_cod_report", queue="payments")
def generate_daily_cod_report() -> dict[str, str]:
    """
    Generate daily summary of Cash-On-Delivery collected vs remitted.
    """
    yesterday = timezone.now().date() - timezone.timedelta(days=1)
    orders_qs = Order.objects.filter(
        payment_method=PaymentMethod.COD,
        payment_status=PaymentStatus.PAID,
        delivered_at__date=yesterday,
    )

    total_cod_collected = orders_qs.aggregate(
        total=Sum("cod_amount") + Sum("fare_amount")
    )["total"] or Decimal("0.00")

    total_remitted = CODRemittance.objects.filter(
        status=CODStatus.VERIFIED,
        verified_at__date=yesterday,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    logger.info(
        "daily_cod_report_generated",
        date=yesterday.isoformat(),
        collected=str(total_cod_collected),
        remitted=str(total_remitted),
    )

    return {
        "date": yesterday.isoformat(),
        "total_cod_collected": str(total_cod_collected),
        "total_remitted": str(total_remitted),
    }
