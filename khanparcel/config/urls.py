# =============================================================================
# Khan Parcel — Root URL Configuration
# =============================================================================

from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def healthz(request: object) -> JsonResponse:
    """Liveness probe — returns 200 if the process is alive."""
    return JsonResponse({"status": "ok"})


def readyz(request: object) -> JsonResponse:
    """Readiness probe — checks DB, Redis, and Celery connectivity."""
    checks: dict[str, str] = {}
    healthy = True

    # Database check
    try:
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        healthy = False

    # Redis check
    try:
        from django_redis import get_redis_connection

        redis_conn = get_redis_connection("default")
        redis_conn.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        healthy = False

    # Celery check
    try:
        from config.celery import app as celery_app

        inspector = celery_app.control.inspect()
        if inspector.ping():
            checks["celery"] = "ok"
        else:
            checks["celery"] = "no workers responding"
            healthy = False
    except Exception as e:
        checks["celery"] = f"error: {e}"
        healthy = False

    status_code = 200 if healthy else 503
    return JsonResponse({"status": "ready" if healthy else "degraded", "checks": checks}, status=status_code)


urlpatterns = [
    # ─── Health ──────────────────────────────────────────────────────────
    path("healthz/", healthz, name="healthz"),
    path("readyz/", readyz, name="readyz"),
    path("api/v1/health/", healthz, name="api-healthz"),

    # ─── Admin ───────────────────────────────────────────────────────────
    path("admin/", admin.site.urls),

    # ─── API v1 ──────────────────────────────────────────────────────────
    path("api/v1/auth/", include("apps.accounts.urls", namespace="accounts")),
    path("api/v1/riders/", include("apps.riders.urls", namespace="riders")),
    path("api/v1/orders/", include("apps.orders.urls", namespace="orders")),
    path("api/v1/dispatch/", include("apps.dispatch.urls", namespace="dispatch")),
    path("api/v1/pricing/", include("apps.pricing.urls", namespace="pricing")),
    path("api/v1/payments/", include("apps.payments.urls", namespace="payments")),
    path("api/v1/tracking/", include("apps.tracking.urls", namespace="tracking")),
    path("api/v1/chat/", include("apps.chat.urls", namespace="chat")),
    path("api/v1/notifications/", include("apps.notifications.urls", namespace="notifications")),
    path("api/v1/support/", include("apps.support.urls", namespace="support")),
    path("api/v1/business/", include("apps.business.urls", namespace="business")),
    path("api/v1/ops/", include("apps.reports.urls", namespace="reports")),

    # ─── Public Tracking ────────────────────────────────────────────────
    path("t/", include("apps.tracking.public_urls", namespace="public_tracking")),

    # ─── OpenAPI / Docs ─────────────────────────────────────────────────
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # ─── Prometheus Metrics ─────────────────────────────────────────────
    path("", include("django_prometheus.urls")),
]

# Serve media in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
