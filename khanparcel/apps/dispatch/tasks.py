# =============================================================================
# Khan Parcel — Dispatch Celery Tasks
# =============================================================================

from __future__ import annotations

import structlog
from celery import shared_task

from apps.dispatch.services import DispatchEngine

logger = structlog.get_logger(__name__)


@shared_task(name="apps.dispatch.tasks.dispatch_order", queue="dispatch")
def dispatch_order(order_id: str) -> bool:
    """Initiate multi-round dispatch matching for an order."""
    logger.info("task_dispatch_order_started", order_id=order_id)
    return DispatchEngine.dispatch_round(order_id=order_id, round_num=1)


@shared_task(name="apps.dispatch.tasks.check_offer_timeout", queue="dispatch")
def check_offer_timeout(offer_id: str) -> None:
    """Verify if dispatch offer was accepted; if not, expire and advance dispatch."""
    DispatchEngine.handle_offer_timeout(offer_id=offer_id)
