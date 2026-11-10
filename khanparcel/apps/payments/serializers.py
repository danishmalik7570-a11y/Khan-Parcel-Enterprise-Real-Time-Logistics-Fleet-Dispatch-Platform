# =============================================================================
# Khan Parcel — Payments Serializers
# =============================================================================

from __future__ import annotations

from rest_framework import serializers

from apps.payments.models import (
    CODRemittance,
    CODStatus,
    LedgerEntry,
    PayoutRequest,
    PayoutStatus,
    Wallet,
)


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = [
            "id",
            "currency",
            "balance",
            "pending_balance",
            "is_frozen",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class WalletTopupSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=100.0)
    payment_method = serializers.CharField(max_length=30)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")


class LedgerEntrySerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True, default="")

    class Meta:
        model = LedgerEntry
        fields = [
            "id",
            "transaction_id",
            "order_number",
            "account_type",
            "entry_type",
            "amount",
            "balance_after",
            "description",
            "created_at",
        ]
        read_only_fields = fields


class PayoutRequestSerializer(serializers.ModelSerializer):
    rider_name = serializers.CharField(source="rider.user.name", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.name", read_only=True)

    class Meta:
        model = PayoutRequest
        fields = [
            "id",
            "rider_name",
            "amount",
            "payout_method",
            "account_title",
            "account_number",
            "bank_name",
            "status",
            "reference_number",
            "rejection_reason",
            "reviewed_by_name",
            "paid_at",
            "created_at",
        ]
        read_only_fields = fields


class PayoutCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=500.0)
    payout_method = serializers.CharField(max_length=30, default="BANK_TRANSFER")
    account_title = serializers.CharField(max_length=150)
    account_number = serializers.CharField(max_length=50)
    bank_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")


class PayoutProcessSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    reference_number = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    rejection_reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class CODRemittanceSerializer(serializers.ModelSerializer):
    rider_name = serializers.CharField(source="rider.user.name", read_only=True)
    verified_by_name = serializers.CharField(source="verified_by.name", read_only=True)

    class Meta:
        model = CODRemittance
        fields = [
            "id",
            "rider_name",
            "amount",
            "status",
            "deposit_slip_image",
            "bank_reference",
            "notes",
            "verified_by_name",
            "verified_at",
            "created_at",
        ]
        read_only_fields = fields


class CODRemittanceSubmitSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1.0)
    bank_reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class CODRemittanceVerifySerializer(serializers.Serializer):
    approve = serializers.BooleanField()
