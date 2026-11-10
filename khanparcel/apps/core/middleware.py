# =============================================================================
# Khan Parcel — Core Middleware
# =============================================================================

from __future__ import annotations

import time
import uuid
from typing import Callable

import structlog
from django.http import HttpRequest, HttpResponse

logger = structlog.get_logger(__name__)


class RequestIDMiddleware:
    """
    Attach a unique request ID to every request.

    If the client sends X-Request-ID, use it; otherwise generate one.
    The ID is available as `request.request_id` and in the response header.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.META.get("HTTP_X_REQUEST_ID", str(uuid.uuid4()))
        request.request_id = request_id  # type: ignore[attr-defined]

        # Bind to structlog context for this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response


class StructlogMiddleware:
    """
    Log every HTTP request with structured fields.

    Logs: method, path, status, duration_ms, user_id, IP.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start_time = time.monotonic()

        # Bind user info if authenticated
        if hasattr(request, "user") and request.user.is_authenticated:
            structlog.contextvars.bind_contextvars(user_id=str(request.user.pk))

        response = self.get_response(request)

        duration_ms = round((time.monotonic() - start_time) * 1000, 2)

        # Skip health checks from logs
        if request.path not in ("/healthz/", "/readyz/", "/metrics"):
            logger.info(
                "http_request",
                method=request.method,
                path=request.path,
                status=response.status_code,
                duration_ms=duration_ms,
                ip=self._get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:200],
            )

        return response

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        """Extract client IP, respecting X-Forwarded-For behind proxy."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")
