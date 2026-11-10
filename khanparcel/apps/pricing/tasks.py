# =============================================================================
# Khan Parcel — Pricing Celery Tasks
# =============================================================================

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

import structlog
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.pricing.models import Quote, SurgeCell
from apps.pricing.services import SurgeService
from apps.riders.models import RiderProfile, RiderStatus

logger = structlog.get_logger(__name__)


@shared_task(name="apps.pricing.tasks.recalculate_surge", queue="default")
def recalculate_surge() -> dict[str, int]:
    """
    Recalculate dynamic surge multipliers across all active H3 spatial cells.
    """
    supply_by_cell: dict[str, int] = defaultdict(int)
    demand_by_cell: dict[str, int] = defaultdict(int)

    # 1. Available riders (Supply)
    available_riders = RiderProfile.objects.filter(
        is_online=True,
        status=RiderStatus.AVAILABLE,
        current_location__isnull=False,
    )
    for rider in available_riders:
        h3_idx = SurgeService.get_h3_index(
            rider.current_location.y,
            rider.current_location.x,
            settings.SURGE_H3_RESOLUTION,
        )
        supply_by_cell[h3_idx] += 1

    # 2. Pending orders created in last 15 min (Demand)
    try:
        from apps.orders.models import Order, OrderStatus

        recent_cutoff = timezone.now() - timezone.timedelta(minutes=15)
        pending_orders = Order.objects.filter(
            status__in=[OrderStatus.CREATED, OrderStatus.SEARCHING_RIDER],
            created_at__gte=recent_cutoff,
        )
        for order in pending_orders:
            h3_idx = SurgeService.get_h3_index(
                order.pickup_point.y,
                order.pickup_point.x,
                settings.SURGE_H3_RESOLUTION,
            )
            demand_by_cell[h3_idx] += 1
    except Exception:
        pass

    all_cells = set(supply_by_cell.keys()) | set(demand_by_cell.keys())
    updated_count = 0

    for h3_idx in all_cells:
        SurgeService.recalculate_cell(
            h3_idx=h3_idx,
            demand_count=demand_by_cell[h3_idx],
            supply_count=supply_by_cell[h3_idx],
        )
        updated_count += 1

    # Reset idle cells back to 1.00
    SurgeCell.objects.exclude(h3_index__in=all_cells).update(
        multiplier=Decimal("1.00"),
        demand_count=0,
        supply_count=0,
        last_calculated_at=timezone.now(),
    )

    logger.info("recalculate_surge_completed", active_cells=updated_count)
    return {"cells_updated": updated_count}


@shared_task(name="apps.pricing.tasks.cleanup_expired_quotes", queue="default")
def cleanup_expired_quotes() -> int:
    """Delete expired quotes that were not converted to orders."""
    cutoff = timezone.now() - timezone.timedelta(hours=24)
    deleted, _ = Quote.objects.filter(expires_at__lt=cutoff, is_accepted=False).delete()
    logger.info("cleanup_expired_quotes", deleted=deleted)
    return deleted
