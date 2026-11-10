# =============================================================================
# Khan Parcel — Test Settings
# =============================================================================
from __future__ import annotations

from .base import *  # noqa: F401, F403

DEBUG = False
SECRET_KEY = "test-secret-key-not-for-production-use"  # noqa: S105

# ─── Database ────────────────────────────────────────────────────────────────
DATABASES["default"]["NAME"] = "test_khanparcel"  # type: ignore[name-defined]  # noqa: F405

# ─── Password Hashing (fast for tests) ──────────────────────────────────────
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ─── Celery (eager mode for tests) ──────────────────────────────────────────
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ─── Channels (in-memory for tests) ─────────────────────────────────────────
CHANNEL_LAYERS = {  # noqa: F811
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# ─── Cache (local memory for tests) ─────────────────────────────────────────
CACHES = {  # noqa: F811
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
    "axes": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}

# ─── Storage (local filesystem for tests) ───────────────────────────────────
STORAGES = {  # noqa: F811
    "default": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# ─── Email ───────────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# ─── Disable throttling in tests ────────────────────────────────────────────
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # type: ignore[name-defined]  # noqa: F405
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}  # type: ignore[name-defined]  # noqa: F405

# ─── Disable Sentry in tests ────────────────────────────────────────────────
SENTRY_DSN = ""

# ─── SMS / FCM disabled ─────────────────────────────────────────────────────
SMS_PROVIDER = "console"
FCM_ENABLED = False

# ─── Disable Axes in tests ──────────────────────────────────────────────────
AXES_ENABLED = False
