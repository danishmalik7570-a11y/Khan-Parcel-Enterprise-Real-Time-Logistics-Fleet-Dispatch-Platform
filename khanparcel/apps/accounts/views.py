# =============================================================================
# Khan Parcel — Accounts Views
# =============================================================================

from __future__ import annotations

from typing import Any

import pyotp
import structlog
from django.conf import settings
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.models import Address, Device, User
from apps.accounts.serializers import (
    AddressSerializer,
    AuthResponseSerializer,
    DeviceDeregisterSerializer,
    DeviceRegisterSerializer,
    DeviceSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    StaffLoginSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.accounts.services import AuthService, OTPService
from apps.core.permissions import IsStaff

logger = structlog.get_logger(__name__)


# ─── OTP Views ──────────────────────────────────────────────────────────────

class OTPRequestView(APIView):
    """
    Request an OTP for phone verification.

    Rate limited: 3 per 10 minutes per phone, 10 per hour per IP.
    Resend cooldown: 30 seconds.
    """

    permission_classes = [permissions.AllowAny]
    throttle_scope = "otp_request"

    @extend_schema(
        request=OTPRequestSerializer,
        responses={200: dict},
        tags=["Auth"],
        summary="Request OTP",
        description="Send an OTP to the given phone number for login/registration.",
    )
    def post(self, request: Request) -> Response:
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        purpose = serializer.validated_data["purpose"]
        ip_address = self._get_client_ip(request)

        result = OTPService.create_and_send(phone, purpose, ip_address)

        if not result["success"]:
            return Response(
                {"error": {"code": result["error"], "message": result["message"]}},
                status=status.HTTP_429_TOO_MANY_REQUESTS
                if result["error"] in ("RATE_LIMIT_EXCEEDED", "COOLDOWN_ACTIVE")
                else status.HTTP_400_BAD_REQUEST,
            )

        return Response(result, status=status.HTTP_200_OK)

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")


class OTPVerifyView(APIView):
    """
    Verify OTP and authenticate user.

    On success, returns JWT tokens and user profile.
    Creates the user account if this is a first-time login.
    """

    permission_classes = [permissions.AllowAny]
    throttle_scope = "otp_verify"

    @extend_schema(
        request=OTPVerifySerializer,
        responses={200: AuthResponseSerializer},
        tags=["Auth"],
        summary="Verify OTP",
        description="Verify OTP code and receive JWT tokens.",
    )
    def post(self, request: Request) -> Response:
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        phone = data["phone"]
        code = data["code"]
        purpose = data["purpose"]

        # Verify OTP
        otp_result = OTPService.verify(phone, code, purpose)
        if not otp_result["success"]:
            return Response(
                {"error": {"code": otp_result["error"], "message": otp_result["message"]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Register or login
        auth_result = AuthService.register_or_login(
            phone=phone,
            name=data.get("name", ""),
            role=data.get("role", "CUSTOMER"),
        )

        user = auth_result["user"]

        # Register device if FCM token provided
        fcm_token = data.get("fcm_token", "")
        platform = data.get("platform", "")
        if fcm_token and platform:
            AuthService.register_device(
                user=user,
                fcm_token=fcm_token,
                platform=platform,
                app_version=data.get("app_version", ""),
            )

        # Generate tokens
        tokens = AuthService.get_tokens_for_user(user)

        return Response(
            {
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "user": UserSerializer(user).data,
                "is_new": auth_result["is_new"],
            },
            status=status.HTTP_200_OK,
        )


# ─── Token Refresh ──────────────────────────────────────────────────────────

class CustomTokenRefreshView(TokenRefreshView):
    """Refresh JWT access token using a valid refresh token."""

    @extend_schema(tags=["Auth"], summary="Refresh Token")
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().post(request, *args, **kwargs)


# ─── Logout ─────────────────────────────────────────────────────────────────

class LogoutView(APIView):
    """Logout by blacklisting the refresh token."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request={"type": "object", "properties": {"refresh": {"type": "string"}}},
        tags=["Auth"],
        summary="Logout",
    )
    def post(self, request: Request) -> Response:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"error": {"code": "MISSING_TOKEN", "message": "Refresh token is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass  # Token may already be blacklisted or invalid

        # Deregister device if FCM token provided
        fcm_token = request.data.get("fcm_token")
        if fcm_token:
            AuthService.deregister_device(request.user, fcm_token)

        return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)


# ─── Staff Login ─────────────────────────────────────────────────────────────

class StaffLoginView(APIView):
    """
    Staff login with email + password + optional TOTP 2FA.

    Only users with ADMIN, DISPATCHER, or SUPPORT roles can log in.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=StaffLoginSerializer,
        responses={200: AuthResponseSerializer},
        tags=["Auth"],
        summary="Staff Login",
    )
    def post(self, request: Request) -> Response:
        serializer = StaffLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        totp_code = serializer.validated_data.get("totp_code")

        # Find user by email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Check password
        if not user.check_password(password):
            return Response(
                {"error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Check staff role
        if not user.has_any_role("ADMIN", "DISPATCHER", "SUPPORT"):
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "Staff access required."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check 2FA if enabled
        if user.totp_enabled:
            if not totp_code:
                return Response(
                    {"error": {"code": "TOTP_REQUIRED", "message": "2FA code is required."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            totp = pyotp.TOTP(user.totp_secret)
            if not totp.verify(totp_code, valid_window=1):
                return Response(
                    {"error": {"code": "INVALID_TOTP", "message": "Invalid 2FA code."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Generate tokens
        tokens = AuthService.get_tokens_for_user(user)

        return Response(
            {
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "user": UserSerializer(user).data,
                "is_new": False,
            },
            status=status.HTTP_200_OK,
        )


# ─── User Profile ───────────────────────────────────────────────────────────

class ProfileView(generics.RetrieveUpdateAPIView):
    """Get or update the authenticated user's profile."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self) -> type:
        if self.request.method in ("PUT", "PATCH"):
            return UserUpdateSerializer
        return UserSerializer

    def get_object(self) -> User:
        return self.request.user

    @extend_schema(tags=["Users"], summary="Get Profile")
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["Users"], summary="Update Profile")
    def put(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().put(request, *args, **kwargs)

    @extend_schema(tags=["Users"], summary="Partial Update Profile")
    def patch(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().patch(request, *args, **kwargs)


# ─── Device Management ──────────────────────────────────────────────────────

class DeviceRegisterView(APIView):
    """Register a device for push notifications."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=DeviceRegisterSerializer,
        responses={200: DeviceSerializer},
        tags=["Users"],
        summary="Register Device",
    )
    def post(self, request: Request) -> Response:
        serializer = DeviceRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        AuthService.register_device(
            user=request.user,
            fcm_token=serializer.validated_data["fcm_token"],
            platform=serializer.validated_data["platform"],
            app_version=serializer.validated_data.get("app_version", ""),
            device_id=serializer.validated_data.get("device_id", ""),
        )

        return Response({"message": "Device registered."}, status=status.HTTP_200_OK)


class DeviceDeregisterView(APIView):
    """Deregister a device from push notifications."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=DeviceDeregisterSerializer,
        tags=["Users"],
        summary="Deregister Device",
    )
    def post(self, request: Request) -> Response:
        serializer = DeviceDeregisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        AuthService.deregister_device(request.user, serializer.validated_data["fcm_token"])

        return Response({"message": "Device deregistered."}, status=status.HTTP_200_OK)


# ─── Address Management ─────────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(tags=["Users"], summary="List Addresses"),
    create=extend_schema(tags=["Users"], summary="Create Address"),
    retrieve=extend_schema(tags=["Users"], summary="Get Address"),
    update=extend_schema(tags=["Users"], summary="Update Address"),
    partial_update=extend_schema(tags=["Users"], summary="Partial Update Address"),
    destroy=extend_schema(tags=["Users"], summary="Delete Address"),
)
class AddressViewSet(viewsets.ModelViewSet):
    """CRUD operations for user's saved addresses."""

    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> Any:
        return Address.objects.filter(user=self.request.user).order_by("-is_default", "-created_at")


# ─── Staff 2FA Setup ────────────────────────────────────────────────────────

class Setup2FAView(APIView):
    """Set up TOTP 2FA for staff accounts."""

    permission_classes = [permissions.IsAuthenticated, IsStaff]

    @extend_schema(tags=["Auth"], summary="Setup 2FA")
    def post(self, request: Request) -> Response:
        user = request.user

        # Generate new secret
        secret = pyotp.random_base32()
        user.totp_secret = secret
        user.save(update_fields=["totp_secret", "updated_at"])

        # Generate provisioning URI
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(
            name=str(user.phone),
            issuer_name=settings.TOTP_ISSUER,
        )

        return Response(
            {
                "secret": secret,
                "uri": uri,
                "message": "Scan the QR code with your authenticator app, then verify with a code.",
            },
            status=status.HTTP_200_OK,
        )


class Verify2FAView(APIView):
    """Verify and enable TOTP 2FA for staff accounts."""

    permission_classes = [permissions.IsAuthenticated, IsStaff]

    @extend_schema(tags=["Auth"], summary="Verify 2FA")
    def post(self, request: Request) -> Response:
        code = request.data.get("code")
        if not code:
            return Response(
                {"error": {"code": "MISSING_CODE", "message": "TOTP code is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        if not user.totp_secret:
            return Response(
                {"error": {"code": "NO_SECRET", "message": "2FA has not been set up. Call POST /2fa/setup first."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(code, valid_window=1):
            return Response(
                {"error": {"code": "INVALID_CODE", "message": "Invalid TOTP code."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.totp_enabled = True
        user.save(update_fields=["totp_enabled", "updated_at"])

        return Response({"message": "2FA enabled successfully."}, status=status.HTTP_200_OK)
