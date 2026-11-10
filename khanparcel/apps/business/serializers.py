# =============================================================================
# Khan Parcel — Business Serializers
# =============================================================================

from __future__ import annotations

from rest_framework import serializers

from apps.business.models import BulkOrderBatch, BusinessProfile


class BusinessProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfile
        fields = [
            "id",
            "company_name",
            "ntn_number",
            "billing_address",
            "contact_person",
            "credit_limit",
            "is_verified",
            "is_monthly_billing",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_verified", "credit_limit", "created_at", "updated_at"]


class BulkOrderBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkOrderBatch
        fields = [
            "id",
            "file",
            "total_count",
            "processed_count",
            "success_count",
            "error_count",
            "status",
            "error_log",
            "created_at",
        ]
        read_only_fields = ["id", "total_count", "processed_count", "success_count", "error_count", "status", "error_log", "created_at"]
