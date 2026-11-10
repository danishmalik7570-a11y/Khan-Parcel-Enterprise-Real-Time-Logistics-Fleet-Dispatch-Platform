# =============================================================================
# Khan Parcel — Accounts Celery Tasks
# =============================================================================

from __future__ import annotations

import structlog
from celery import shared_task
from django.utils import timezone

from apps.accounts.models import OTPCode

logger = structlog.get_logger(__name__)


@shared_task(name="apps.accounts.tasks.cleanup_expired_otps", queue="default")
def cleanup_expired_otps() -> int:
    """Delete OTP codes that expired more than 24 hours ago."""
    cutoff = timezone.now() - timezone.timedelta(hours=24)
    deleted, _ = OTPCode.objects.filter(expires_at__lt=cutoff).delete()
    logger.info("cleanup_expired_otps", deleted=deleted)
    return deleted
