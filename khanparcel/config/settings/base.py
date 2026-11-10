# =============================================================================
# Khan Parcel — Base Settings
# =============================================================================
# Common settings shared across all environments.
# Environment-specific overrides in dev.py / prod.py / test.py.
# =============================================================================

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from typing import Any

import environ

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
APPS_DIR = BASE_DIR / "apps"

# ─── Environment ─────────────────────────────────────────────────────────────
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_SECRET_KEY=(str, "django-insecure-khanparcel-dev-secret-key-change-in-prod-!@#$"),
)
environ.Env.read_env(str(BASE_DIR / ".env"))

# ─── Core ────────────────────────────────────────────────────────────────────
SECRET_KEY: str = env("DJANGO_SECRET_KEY")
DEBUG: bool = env("DJANGO_DEBUG")
ALLOWED_HOSTS: list[str] = env("DJANGO_ALLOWED_HOSTS")

# ─── Application Definition ─────────────────────────────────────────────────
from apps.core.gis_compat import HAS_GDAL

DJANGO_APPS: list[str] = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
if HAS_GDAL:
    DJANGO_APPS += ["django.contrib.gis", "django.contrib.postgres"]


THIRD_PARTY_APPS: list[str] = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_filters",
    "corsheaders",
    "channels",
    "django_celery_results",
    "django_celery_beat",
    "django_redis",
    "simple_history",
    "import_export",
    "phonenumber_field",
    "djmoney",
    "axes",
    "django_prometheus",
    "storages",
]

LOCAL_APPS: list[str] = [
    "apps.core",
    "apps.accounts",
    "apps.riders",
    "apps.orders",
    "apps.dispatch",
    "apps.pricing",
    "apps.payments",
    "apps.realtime",
    "apps.tracking",
    "apps.chat",
    "apps.notifications",
    "apps.support",
    "apps.business",
    "apps.reports",
]

INSTALLED_APPS: list[str] = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─── Middleware ──────────────────────────────────────────────────────────────
MIDDLEWARE: list[str] = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "apps.core.middleware.RequestIDMiddleware",
    "apps.core.middleware.StructlogMiddleware",
    "axes.middleware.AxesMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

# ─── URL Configuration ──────────────────────────────────────────────────────
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ─── Templates ───────────────────────────────────────────────────────────────
TEMPLATES: list[dict[str, Any]] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ─── Database ────────────────────────────────────────────────────────────────
USE_SQLITE: bool = env.bool("USE_SQLITE", default=not HAS_GDAL)

if USE_SQLITE:
    DATABASES: dict[str, Any] = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES: dict[str, Any] = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis" if HAS_GDAL else "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", default="khanparcel"),
            "USER": env("POSTGRES_USER", default="khanparcel"),
            "PASSWORD": env("POSTGRES_PASSWORD", default="khanparcel_secret"),
            "HOST": env("POSTGRES_HOST", default="localhost"),
            "PORT": env.int("POSTGRES_PORT", default=5432),
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {
                "connect_timeout": 10,
            },
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Custom User Model ──────────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.User"

# ─── Authentication Backends ────────────────────────────────────────────────
AUTHENTICATION_BACKENDS: list[str] = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# ─── Password Validation ────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── Internationalization ───────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ─── Static & Media ─────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS: list[Path] = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ─── Redis ───────────────────────────────────────────────────────────────────
REDIS_URL: str = env("REDIS_URL", default="redis://localhost:6379/0")
REDIS_CACHE_URL: str = env("REDIS_CACHE_URL", default="redis://localhost:6379/1")
REDIS_CELERY_URL: str = env("REDIS_CELERY_URL", default="redis://localhost:6379/2")

# ─── Cache ───────────────────────────────────────────────────────────────────
CACHES: dict[str, Any] = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SERIALIZER": "django_redis.serializers.json.JSONSerializer",
        },
        "KEY_PREFIX": "kp",
        "TIMEOUT": 300,
    },
    "axes": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "axes",
        "TIMEOUT": 900,
    },
}

# ─── Django Channels ─────────────────────────────────────────────────────────
CHANNEL_LAYERS: dict[str, Any] = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
            "capacity": 1500,
            "expiry": 60,
        },
    },
}

# ─── Django REST Framework ───────────────────────────────────────────────────
REST_FRAMEWORK: dict[str, Any] = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "120/minute",
        "otp_request": "3/10min",
        "otp_verify": "5/minute",
        "quote": "60/minute",
        "location": "60/minute",
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S.%fZ",
    "DATE_FORMAT": "%Y-%m-%d",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

# ─── SimpleJWT ───────────────────────────────────────────────────────────────
SIMPLE_JWT: dict[str, Any] = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=15)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env.int("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=30)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "apps.accounts.serializers.CustomTokenObtainPairSerializer",
}

# ─── DRF Spectacular (OpenAPI) ───────────────────────────────────────────────
SPECTACULAR_SETTINGS: dict[str, Any] = {
    "TITLE": "Khan Parcel API",
    "DESCRIPTION": "Real-time logistics and delivery platform API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
    },
    "TAGS": [
        {"name": "Auth", "description": "Authentication & OTP"},
        {"name": "Users", "description": "User management"},
        {"name": "Riders", "description": "Rider profiles & documents"},
        {"name": "Orders", "description": "Order lifecycle"},
        {"name": "Dispatch", "description": "Dispatch & offers"},
        {"name": "Pricing", "description": "Quotes & pricing rules"},
        {"name": "Payments", "description": "Wallets, ledger & payouts"},
        {"name": "Tracking", "description": "Location & public tracking"},
        {"name": "Chat", "description": "In-order messaging"},
        {"name": "Notifications", "description": "Push & SMS"},
        {"name": "Support", "description": "Tickets & SOS"},
        {"name": "Business", "description": "Business accounts & bulk"},
        {"name": "Ops", "description": "Admin/Dispatcher operations"},
        {"name": "Reports", "description": "Analytics & exports"},
        {"name": "Health", "description": "System health checks"},
    ],
}

# ─── Celery ──────────────────────────────────────────────────────────────────
CELERY_BROKER_URL: str = env("CELERY_BROKER_URL", default=REDIS_CELERY_URL)
CELERY_RESULT_BACKEND: str = env("CELERY_RESULT_BACKEND", default="django-db")
CELERY_RESULT_EXTENDED: bool = True
CELERY_ACCEPT_CONTENT: list[str] = ["json"]
CELERY_TASK_SERIALIZER: str = "json"
CELERY_RESULT_SERIALIZER: str = "json"
CELERY_TIMEZONE: str = TIME_ZONE
CELERY_TASK_TRACK_STARTED: bool = True
CELERY_TASK_TIME_LIMIT: int = 300  # 5 min hard limit
CELERY_TASK_SOFT_TIME_LIMIT: int = 240  # 4 min soft limit
CELERY_WORKER_MAX_TASKS_PER_CHILD: int = 1000
CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1
CELERY_TASK_ACKS_LATE: bool = True
CELERY_TASK_REJECT_ON_WORKER_LOST: bool = True
CELERY_TASK_DEFAULT_QUEUE: str = "default"
CELERY_TASK_QUEUES: dict[str, dict[str, str]] = {
    "default": {"exchange": "default", "routing_key": "default"},
    "dispatch": {"exchange": "dispatch", "routing_key": "dispatch"},
    "notifications": {"exchange": "notifications", "routing_key": "notifications"},
    "payments": {"exchange": "payments", "routing_key": "payments"},
    "reports": {"exchange": "reports", "routing_key": "reports"},
}
CELERY_BEAT_SCHEDULE: dict[str, Any] = {
    "recalculate-surge": {
        "task": "apps.pricing.tasks.recalculate_surge",
        "schedule": env.int("SURGE_RECALC_INTERVAL_SECONDS", default=60),
    },
    "auto-offline-stale-riders": {
        "task": "apps.riders.tasks.auto_offline_stale_riders",
        "schedule": 30.0,
    },
    "cleanup-expired-otps": {
        "task": "apps.accounts.tasks.cleanup_expired_otps",
        "schedule": 3600.0,  # hourly
    },
    "cleanup-expired-quotes": {
        "task": "apps.pricing.tasks.cleanup_expired_quotes",
        "schedule": 600.0,  # every 10 min
    },
    "daily-cod-report": {
        "task": "apps.payments.tasks.generate_daily_cod_report",
        "schedule": {
            "hour": 2,
            "minute": 0,
        },
    },
}

# ─── Storage (S3 / MinIO) ───────────────────────────────────────────────────
STORAGE_BACKEND: str = env("STORAGE_BACKEND", default="minio")

if STORAGE_BACKEND in ("s3", "minio"):
    STORAGES: dict[str, Any] = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    AWS_ACCESS_KEY_ID: str = env("AWS_ACCESS_KEY_ID", default="minioadmin")
    AWS_SECRET_ACCESS_KEY: str = env("AWS_SECRET_ACCESS_KEY", default="minioadmin")
    AWS_STORAGE_BUCKET_NAME: str = env("AWS_STORAGE_BUCKET_NAME", default="khanparcel-media")
    AWS_S3_ENDPOINT_URL: str | None = env("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_REGION_NAME: str = env("AWS_S3_REGION_NAME", default="us-east-1")
    AWS_S3_USE_SSL: bool = env.bool("AWS_S3_USE_SSL", default=False)
    AWS_S3_FILE_OVERWRITE: bool = False
    AWS_DEFAULT_ACL: str | None = None
    AWS_QUERYSTRING_AUTH: bool = True
    AWS_QUERYSTRING_EXPIRE: int = 900  # 15-minute signed URLs

# ─── Phone Number ────────────────────────────────────────────────────────────
PHONENUMBER_DEFAULT_REGION = "PK"
PHONENUMBER_DEFAULT_FORMAT = "E164"

# ─── OTP Configuration ──────────────────────────────────────────────────────
OTP_LENGTH: int = env.int("OTP_LENGTH", default=6)
OTP_TTL_SECONDS: int = env.int("OTP_TTL_SECONDS", default=300)
OTP_MAX_ATTEMPTS: int = env.int("OTP_MAX_ATTEMPTS", default=5)
OTP_RESEND_COOLDOWN_SECONDS: int = env.int("OTP_RESEND_COOLDOWN_SECONDS", default=30)

# ─── Firebase / FCM ─────────────────────────────────────────────────────────
FIREBASE_CREDENTIALS_PATH: str | None = env("FIREBASE_CREDENTIALS_PATH", default=None)
FCM_ENABLED: bool = env.bool("FCM_ENABLED", default=False)

# ─── SMS ─────────────────────────────────────────────────────────────────────
SMS_PROVIDER: str = env("SMS_PROVIDER", default="console")
TWILIO_ACCOUNT_SID: str = env("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN: str = env("TWILIO_AUTH_TOKEN", default="")
TWILIO_FROM_NUMBER: str = env("TWILIO_FROM_NUMBER", default="")

# ─── Routing / Maps ─────────────────────────────────────────────────────────
ROUTING_PROVIDER: str = env("ROUTING_PROVIDER", default="osrm")
OSRM_BASE_URL: str = env("OSRM_BASE_URL", default="http://osrm:5000")
MAPBOX_ACCESS_TOKEN: str = env("MAPBOX_ACCESS_TOKEN", default="")
GOOGLE_MAPS_API_KEY: str = env("GOOGLE_MAPS_API_KEY", default="")

# ─── Dispatch ────────────────────────────────────────────────────────────────
DISPATCH_MAX_ROUNDS: int = env.int("DISPATCH_MAX_ROUNDS", default=4)
DISPATCH_RADII_KM: list[int] = [int(r) for r in env.list("DISPATCH_RADII_KM", default=[2, 4, 7, 10])]
DISPATCH_OFFER_TTL_SECONDS: int = env.int("DISPATCH_OFFER_TTL_SECONDS", default=15)
DISPATCH_MAX_CONCURRENT_JOBS: int = env.int("DISPATCH_MAX_CONCURRENT_JOBS", default=3)
DISPATCH_SCORE_WEIGHTS: dict[str, float] = {
    "eta": env.float("DISPATCH_SCORE_W1", default=0.35),
    "rating": env.float("DISPATCH_SCORE_W2", default=0.20),
    "acceptance_rate": env.float("DISPATCH_SCORE_W3", default=0.15),
    "idle_time": env.float("DISPATCH_SCORE_W4", default=0.10),
    "cancel_rate": env.float("DISPATCH_SCORE_W5", default=0.10),
    "current_load": env.float("DISPATCH_SCORE_W6", default=0.10),
}

# ─── Geofence ────────────────────────────────────────────────────────────────
GEOFENCE_RADIUS_METERS: int = env.int("GEOFENCE_RADIUS_METERS", default=150)

# ─── Surge ───────────────────────────────────────────────────────────────────
SURGE_MAX_MULTIPLIER: float = env.float("SURGE_MAX_MULTIPLIER", default=2.5)
SURGE_H3_RESOLUTION: int = env.int("SURGE_H3_RESOLUTION", default=8)
SURGE_EMA_ALPHA: float = env.float("SURGE_EMA_ALPHA", default=0.3)

# ─── Pricing ────────────────────────────────────────────────────────────────
QUOTE_EXPIRY_SECONDS: int = env.int("QUOTE_EXPIRY_SECONDS", default=300)
QUOTE_SURGE_DRIFT_THRESHOLD: float = env.float("QUOTE_SURGE_DRIFT_THRESHOLD", default=0.10)

# ─── CORS ────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS: list[str] = env.list("CORS_ALLOWED_ORIGINS", default=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
])
CORS_ALLOW_CREDENTIALS: bool = True
CORS_ALLOW_HEADERS: list[str] = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-idempotency-key",
    "x-request-id",
]

# ─── Security ────────────────────────────────────────────────────────────────
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# ─── Axes (Brute-force protection) ──────────────────────────────────────────
AXES_FAILURE_LIMIT: int = 5
AXES_COOLOFF_TIME: timedelta = timedelta(minutes=15)
AXES_LOCK_OUT_AT_FAILURE: bool = True
AXES_RESET_ON_SUCCESS: bool = True
AXES_CACHE: str = "axes"
AXES_LOCKOUT_CALLABLE = "apps.core.exceptions.axes_lockout_response"

# ─── Sentry ──────────────────────────────────────────────────────────────────
SENTRY_DSN: str = env("SENTRY_DSN", default="")
SENTRY_ENVIRONMENT: str = env("SENTRY_ENVIRONMENT", default="development")
SENTRY_TRACES_SAMPLE_RATE: float = env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1)

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        send_default_pii=False,
    )

# ─── Structlog ───────────────────────────────────────────────────────────────
import structlog  # noqa: E402

LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer() if DEBUG else structlog.processors.JSONRenderer(),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# ─── 2FA / TOTP ─────────────────────────────────────────────────────────────
TOTP_ISSUER: str = env("TOTP_ISSUER", default="KhanParcel")

# ─── Seed Data ───────────────────────────────────────────────────────────────
SEED_CENTER_LAT: float = env.float("SEED_CENTER_LAT", default=33.6844)
SEED_CENTER_LNG: float = env.float("SEED_CENTER_LNG", default=73.0479)
SEED_NUM_RIDERS: int = env.int("SEED_NUM_RIDERS", default=50)
SEED_NUM_ORDERS: int = env.int("SEED_NUM_ORDERS", default=200)

# ─── File Upload Limits ─────────────────────────────────────────────────────
FILE_UPLOAD_MAX_MEMORY_SIZE: int = 10 * 1024 * 1024  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE: int = 10 * 1024 * 1024  # 10 MB
MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]
ALLOWED_DOCUMENT_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp", "application/pdf"]
