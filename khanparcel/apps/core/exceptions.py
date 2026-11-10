# =============================================================================
# Khan Parcel — Core Exception Handling
# =============================================================================

from __future__ import annotations

import uuid
from typing import Any

import structlog
from django.http import JsonResponse
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = structlog.get_logger(__name__)


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """
    Custom DRF exception handler that normalizes error responses.

    Response format:
    {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Human-readable message",
            "details": {...},
            "request_id": "uuid"
        }
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_code = getattr(exc, "default_code", "error").upper()
        error_data: dict[str, Any] = {
            "error": {
                "code": error_code,
                "message": str(exc.detail) if hasattr(exc, "detail") else str(exc),
                "request_id": str(context.get("request", {}).META.get("HTTP_X_REQUEST_ID", uuid.uuid4()))
                if hasattr(context.get("request", {}), "META")
                else str(uuid.uuid4()),
            }
        }

        # Include field-level validation errors
        if hasattr(exc, "detail"):
            if isinstance(exc.detail, dict):
                error_data["error"]["details"] = exc.detail
            elif isinstance(exc.detail, list):
                error_data["error"]["details"] = exc.detail

        response.data = error_data

        logger.warning(
            "api_error",
            code=error_code,
            status=response.status_code,
            detail=str(exc),
        )
    else:
        # Unhandled exception — log and return 500
        logger.exception("unhandled_exception", exc_info=exc)

    return response


def axes_lockout_response(request: Any, credentials: Any, *args: Any, **kwargs: Any) -> JsonResponse:
    """Custom response when django-axes locks out a user."""
    return JsonResponse(
        {
            "error": {
                "code": "ACCOUNT_LOCKED",
                "message": "Too many failed login attempts. Please try again in 15 minutes.",
            }
        },
        status=403,
    )


# ─── Custom API Exceptions ──────────────────────────────────────────────────

class OrderStateError(APIException):
    """Raised when an order state transition is invalid."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Invalid order state transition."
    default_code = "ORDER_STATE_ERROR"


class PriceChangedError(APIException):
    """Raised when the price has changed since the quote was generated."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Price has changed. Please confirm the new quote."
    default_code = "PRICE_CHANGED"


class QuoteExpiredError(APIException):
    """Raised when a pricing quote has expired."""

    status_code = status.HTTP_410_GONE
    default_detail = "Quote has expired. Please request a new quote."
    default_code = "QUOTE_EXPIRED"


class GeofenceError(APIException):
    """Raised when a rider is outside the required geofence."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "You are too far from the required location."
    default_code = "GEOFENCE_ERROR"


class OTPVerificationError(APIException):
    """Raised when OTP verification fails."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid or expired OTP."
    default_code = "OTP_VERIFICATION_ERROR"


class InsufficientBalanceError(APIException):
    """Raised when a wallet has insufficient balance."""

    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = "Insufficient wallet balance."
    default_code = "INSUFFICIENT_BALANCE"


class DispatchError(APIException):
    """Raised when dispatch cannot find a rider."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Unable to find a rider at this time."
    default_code = "DISPATCH_ERROR"


class DuplicateRequestError(APIException):
    """Raised when a duplicate idempotency key is detected."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Duplicate request detected."
    default_code = "DUPLICATE_REQUEST"


class RateLimitExceededError(APIException):
    """Raised when a rate limit is exceeded."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Rate limit exceeded. Please try again later."
    default_code = "RATE_LIMIT_EXCEEDED"


class FileValidationError(APIException):
    """Raised when an uploaded file fails validation."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid file upload."
    default_code = "FILE_VALIDATION_ERROR"
