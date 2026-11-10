# =============================================================================
# Khan Parcel — Production Settings
# =============================================================================
from __future__ import annotations

from .base import *  # noqa: F401, F403

DEBUG = False

# ─── Security ────────────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# ─── Email ───────────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST")  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", default=587)  # noqa: F405
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")  # noqa: F405
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")  # noqa: F405
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@khanparcel.com")  # noqa: F405

# ─── Caches ──────────────────────────────────────────────────────────────────
CACHES["default"]["TIMEOUT"] = 600  # type: ignore[name-defined]  # noqa: F405

# ─── Logging Level ───────────────────────────────────────────────────────────
LOGGING["loggers"]["apps"]["level"] = "INFO"  # type: ignore[name-defined]  # noqa: F405
LOGGING["loggers"]["django"]["level"] = "WARNING"  # type: ignore[name-defined]  # noqa: F405

# ─── Static Files ────────────────────────────────────────────────────────────
STORAGES["staticfiles"] = {  # type: ignore[name-defined]  # noqa: F405
    "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
}

# ─── Content Security Policy (if django-csp is available) ────────────────────
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_CONNECT_SRC = ("'self'", "wss:")
