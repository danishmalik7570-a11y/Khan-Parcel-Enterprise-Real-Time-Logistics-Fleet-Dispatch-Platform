# =============================================================================
# Khan Parcel — Development Settings
# =============================================================================
from __future__ import annotations

from .base import *  # noqa: F401, F403

DEBUG = True

# Allow all hosts in dev
ALLOWED_HOSTS = ["*"]

# Add browsable API renderer in dev
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # type: ignore[name-defined]  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

# Use console email backend
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="localhost")  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", default=1025)  # noqa: F405
EMAIL_USE_TLS = False

# Relaxed throttle rates for dev
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # type: ignore[name-defined]  # noqa: F405
    "anon": "600/minute",
    "user": "1200/minute",
    "otp_request": "30/10min",
    "otp_verify": "50/minute",
    "quote": "600/minute",
    "location": "600/minute",
}

# Debug toolbar (opt-in via env)
if env.bool("ENABLE_DEBUG_TOOLBAR", default=False):
    try:
        import debug_toolbar  # noqa: F401

        INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
        MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
        INTERNAL_IPS = ["127.0.0.1", "localhost"]
    except ImportError:
        pass


# CORS: allow all in dev
CORS_ALLOW_ALL_ORIGINS = True

# In-memory Redis/Channel/Celery fallbacks for local dev without Docker
USE_REDIS = env.bool("USE_REDIS", default=False)
if not USE_REDIS:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "kp-dev-cache",
        },
        "axes": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "kp-dev-axes",
        },
    }
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
