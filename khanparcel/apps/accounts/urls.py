# =============================================================================
# Khan Parcel — Accounts URLs
# =============================================================================

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    AddressViewSet,
    CustomTokenRefreshView,
    DeviceDeregisterView,
    DeviceRegisterView,
    LogoutView,
    OTPRequestView,
    OTPVerifyView,
    ProfileView,
    Setup2FAView,
    StaffLoginView,
    Verify2FAView,
)

app_name = "accounts"

router = DefaultRouter()
router.register(r"addresses", AddressViewSet, basename="address")

urlpatterns = [
    path("otp/request/", OTPRequestView.as_view(), name="otp-request"),
    path("otp/verify/", OTPVerifyView.as_view(), name="otp-verify"),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("staff/login/", StaffLoginView.as_view(), name="staff-login"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("devices/register/", DeviceRegisterView.as_view(), name="device-register"),
    path("devices/deregister/", DeviceDeregisterView.as_view(), name="device-deregister"),
    path("2fa/setup/", Setup2FAView.as_view(), name="2fa-setup"),
    path("2fa/verify/", Verify2FAView.as_view(), name="2fa-verify"),
    path("", include(router.urls)),
]
