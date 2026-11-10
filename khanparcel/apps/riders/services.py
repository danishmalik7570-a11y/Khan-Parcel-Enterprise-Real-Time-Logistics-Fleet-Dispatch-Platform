# =============================================================================
# Khan Parcel — Riders Services
# =============================================================================

from __future__ import annotations

from typing import Any

import structlog
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.riders.models import (
    DocumentStatus,
    DocumentType,
    ReviewStatus,
    RiderDocument,
    RiderProfile,
    RiderStatus,
    Vehicle,
)

logger = structlog.get_logger(__name__)


class RiderService:
    @staticmethod
    def get_or_create_profile(user: User) -> RiderProfile:
        profile, created = RiderProfile.objects.get_or_create(user=user)
        if created and UserRole.RIDER not in user.roles:
            user.add_role(UserRole.RIDER)
        return profile

    @classmethod
    def submit_onboarding(cls, user: User, data: dict[str, Any]) -> RiderProfile:
        with transaction.atomic():
            profile = cls.get_or_create_profile(user)
            profile.cnic_number = data["cnic_number"]
            profile.license_number = data["license_number"]
            profile.emergency_contact_name = data["emergency_contact_name"]
            profile.emergency_contact_phone = data["emergency_contact_phone"]
            profile.review_status = ReviewStatus.PENDING_REVIEW
            profile.save()

            Vehicle.objects.create(
                rider=profile,
                vehicle_type=data["vehicle_type"],
                make=data["vehicle_make"],
                model=data["vehicle_model"],
                year=data["vehicle_year"],
                color=data["vehicle_color"],
                plate_number=data["vehicle_plate"],
                is_active=True,
            )

            logger.info("rider_onboarding_submitted", user_id=str(user.id), cnic=profile.cnic_number)
            return profile

    @classmethod
    def upload_document(cls, profile: RiderProfile, doc_type: str, file_obj: Any) -> RiderDocument:
        doc, _ = RiderDocument.objects.update_or_create(
            rider=profile,
            document_type=doc_type,
            defaults={
                "file": file_obj,
                "status": DocumentStatus.PENDING,
                "rejection_reason": "",
            },
        )
        logger.info("rider_document_uploaded", rider_id=str(profile.id), doc_type=doc_type)
        return doc

    @classmethod
    def review_document(
        cls,
        document_id: str,
        admin_user: User,
        status: str,
        rejection_reason: str = "",
    ) -> RiderDocument:
        with transaction.atomic():
            doc = RiderDocument.objects.select_for_update().get(id=document_id)
            doc.status = status
            doc.rejection_reason = rejection_reason if status == DocumentStatus.REJECTED else ""
            doc.verified_by = admin_user
            doc.verified_at = timezone.now()
            doc.save()

            profile = doc.rider
            if status == DocumentStatus.REJECTED:
                profile.review_status = ReviewStatus.REJECTED
                profile.rejection_reason = f"Document rejected ({doc.document_type}): {rejection_reason}"
                profile.save(update_fields=["review_status", "rejection_reason", "updated_at"])
            else:
                cls.check_and_approve_rider_profile(profile, admin_user)

            logger.info(
                "rider_document_reviewed",
                doc_id=str(doc.id),
                status=status,
                admin_id=str(admin_user.id),
            )
            return doc

    @classmethod
    def check_and_approve_rider_profile(cls, profile: RiderProfile, admin_user: User | None = None) -> bool:
        required_types = [
            DocumentType.CNIC_FRONT,
            DocumentType.CNIC_BACK,
            DocumentType.DRIVING_LICENSE,
        ]
        approved_count = RiderDocument.objects.filter(
            rider=profile,
            document_type__in=required_types,
            status=DocumentStatus.APPROVED,
        ).count()

        if approved_count >= len(required_types):
            profile.review_status = ReviewStatus.APPROVED
            profile.rejection_reason = ""
            if admin_user:
                profile.reviewed_by = admin_user
                profile.reviewed_at = timezone.now()
            profile.save(update_fields=["review_status", "rejection_reason", "reviewed_by", "reviewed_at", "updated_at"])
            logger.info("rider_profile_approved", rider_id=str(profile.id))
            return True
        return False

    @classmethod
    def update_location(
        cls,
        profile: RiderProfile,
        lat: float,
        lng: float,
        heading: float | None = None,
        speed: float | None = None,
        battery_level: int | None = None,
    ) -> None:
        profile.update_location(lat=lat, lng=lng, heading=heading, speed=speed, battery=battery_level)

        # Broadcast telemetry to dispatcher and active order tracking channels
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                payload = {
                    "type": "rider_location_update",
                    "rider_id": str(profile.id),
                    "lat": lat,
                    "lng": lng,
                    "heading": heading,
                    "speed": speed,
                    "status": profile.status,
                    "timestamp": timezone.now().isoformat(),
                }
                async_to_sync(channel_layer.group_send)("dispatchers", payload)
                async_to_sync(channel_layer.group_send)(f"rider_{profile.id}", payload)
        except Exception as e:
            logger.warning("ws_broadcast_failed", error=str(e))

    @classmethod
    def toggle_online(cls, profile: RiderProfile, is_online: bool) -> RiderProfile:
        if is_online:
            profile.go_online()
        else:
            profile.go_offline()

        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    "dispatchers",
                    {
                        "type": "rider_status_update",
                        "rider_id": str(profile.id),
                        "status": profile.status,
                        "is_online": profile.is_online,
                    },
                )
        except Exception:
            pass

        return profile
