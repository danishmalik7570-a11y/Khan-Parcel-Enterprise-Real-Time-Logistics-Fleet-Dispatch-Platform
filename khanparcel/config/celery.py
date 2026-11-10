# =============================================================================
# Khan Parcel — Celery Application
# =============================================================================

from __future__ import annotations

import os

from celery import Celery
from celery.signals import setup_logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("khanparcel")

# Load config from Django settings, namespace='CELERY'
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


@setup_logging.connect
def configure_logging(**kwargs: object) -> None:
    """Use Django's logging configuration for Celery workers."""
    import logging.config

    from django.conf import settings

    logging.config.dictConfig(settings.LOGGING)


@app.task(bind=True, ignore_result=True)
def debug_task(self: Celery) -> None:
    """Debug task that prints its own request info."""
    print(f"Request: {self.request!r}")  # noqa: T201
