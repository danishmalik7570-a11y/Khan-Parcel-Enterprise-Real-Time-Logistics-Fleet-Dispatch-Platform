# =============================================================================
# Khan Parcel — Core Permissions
# =============================================================================

from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsAdmin(BasePermission):
    """Allow access only to users with the ADMIN role."""

    message = "Admin access required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_role("ADMIN")
        )


class IsDispatcher(BasePermission):
    """Allow access only to users with the DISPATCHER role."""

    message = "Dispatcher access required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_role("DISPATCHER")
        )


class IsAdminOrDispatcher(BasePermission):
    """Allow access to users with ADMIN or DISPATCHER role."""

    message = "Admin or Dispatcher access required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_any_role("ADMIN", "DISPATCHER")
        )



class IsStaff(BasePermission):
    """Allow access to ADMIN, DISPATCHER, or SUPPORT roles."""

    message = "Staff access required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_any_role("ADMIN", "DISPATCHER", "SUPPORT")
        )


class IsRider(BasePermission):
    """Allow access only to users with the RIDER role."""

    message = "Rider access required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_role("RIDER")
        )


class IsCustomer(BasePermission):
    """Allow access only to users with the CUSTOMER role."""

    message = "Customer access required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_role("CUSTOMER")
        )


class IsBusiness(BasePermission):
    """Allow access only to users with the BUSINESS role."""

    message = "Business account access required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_role("BUSINESS")
        )


class IsOwnerOrStaff(BasePermission):
    """Allow access if the user owns the object or is staff."""

    message = "You do not have permission to access this resource."

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if request.user.has_any_role("ADMIN", "DISPATCHER", "SUPPORT"):
            return True
        # Check common owner field patterns
        if hasattr(obj, "user"):
            return obj.user == request.user
        if hasattr(obj, "customer"):
            return obj.customer == request.user
        if hasattr(obj, "owner"):
            return obj.owner == request.user
        return False


class IsOrderParticipant(BasePermission):
    """Allow access to the customer, assigned rider, or staff."""

    message = "You are not a participant in this order."

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if request.user.has_any_role("ADMIN", "DISPATCHER", "SUPPORT"):
            return True
        if hasattr(obj, "customer") and obj.customer == request.user:
            return True
        if hasattr(obj, "rider") and obj.rider and obj.rider.user == request.user:
            return True
        return False


class ReadOnly(BasePermission):
    """Allow read-only access (GET, HEAD, OPTIONS)."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return request.method in ("GET", "HEAD", "OPTIONS")
