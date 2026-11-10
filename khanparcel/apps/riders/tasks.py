# =============================================================================
# Khan Parcel — Riders Celery Tasks
# =============================================================================

from __future__ import annotations

import structlog
from celery import shared_task
from django.utils import timezone

from apps.riders.models import RiderProfile, RiderStatus
from apps.riders.services import RiderService

logger = structlog.get_logger(__name__)


@shared_task(name="apps.riders.tasks.auto_offline_stale_riders", queue="default")
def auto_offline_stale_riders() -> int:
    """
    Mark riders as offline if their heartbeat hasn't been received in 90 seconds.
    """
    cutoff = timezone.now() - timezone.timedelta(seconds=90)
    stale_riders = RiderProfile.objects.filter(
        is_online=True,
        last_heartbeat_at__lt=cutoff,
    )

    count = 0
    for rider in stale_riders:
        RiderService.toggle_online(rider, is_online=False)
        count += 1

    if count > 0:
        logger.info("auto_offline_stale_riders", marked_offline=count)
    return count
