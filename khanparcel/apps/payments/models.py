# =============================================================================
# Khan Parcel — Payments Models
# =============================================================================

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import BaseModel
from apps.orders.models import Order
from apps.riders.models import RiderProfile


class LedgerAccountType(models.TextChoices):
    CUSTOMER_WALLET = "CUSTOMER_WALLET", "Customer Wallet"
    RIDER_EARNINGS = "RIDER_EARNINGS", "Rider Earnings"
    RIDER_COD_HOLDING = "RIDER_COD_HOLDING", "Rider COD Cash Holding"
    COMPANY_COMMISSION = "COMPANY_COMMISSION", "Company Platform Commission"
    GATEWAY_CLEARING = "GATEWAY_CLEARING", "Payment Gateway Clearing"
    PROMO_EXPENSE = "PROMO_EXPENSE", "Promotion Marketing Expense"


class EntryType(models.TextChoices):
    CREDIT = "CREDIT", "Credit (+)"
    DEBIT = "DEBIT", "Debit (-)"


class PayoutStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    PAID = "PAID", "Paid"
    REJECTED = "REJECTED", "Rejected"


class CODStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Bank Deposit"
    SUBMITTED = "SUBMITTED", "Slip Submitted"
    VERIFIED = "VERIFIED", "Verified & Cleared"
    DISPUTED = "DISPUTED", "Disputed"


class Wallet(BaseModel):
    """User digital wallet for fare prepayments and rider earnings."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="wallet",
    )
    currency = models.CharField(max_length=3, default="PKR")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    pending_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_frozen = models.BooleanField(default=False)

    class Meta:
        db_table = "payments_wallet"
        verbose_name = "Wallet"
        verbose_name_plural = "Wallets"

    def __str__(self) -> str:
        return f"Wallet {self.user.name}: {self.balance} {self.currency}"


class LedgerEntry(BaseModel):
    """
    Immutable double-entry financial transaction log.
    Ensures zero-sum integrity across all accounts.
    """

    transaction_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    order = models.ForeignKey(
        Order,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ledger_entries",
    )
    wallet = models.ForeignKey(
        Wallet,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ledger_entries",
    )
    account_type = models.CharField(max_length=30, choices=LedgerAccountType.choices, db_index=True)
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    description = models.CharField(max_length=255)

    class Meta:
        db_table = "payments_ledger"
        verbose_name = "Ledger Entry"
        verbose_name_plural = "Ledger Entries"
        indexes = [
            models.Index(fields=["transaction_id"], name="idx_ledger_tx"),
            models.Index(fields=["account_type", "created_at"], name="idx_ledger_acc_date"),
        ]

    def __str__(self) -> str:
        return f"{self.entry_type} {self.amount} PKR ({self.account_type}) - {self.description}"


class CODRemittance(BaseModel):
    """Rider cash settlement submission for collected COD funds."""

    rider = models.ForeignKey(
        RiderProfile,
        on_delete=models.CASCADE,
        related_name="cod_remittances",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=CODStatus.choices, default=CODStatus.SUBMITTED, db_index=True)
    deposit_slip_image = models.ImageField(upload_to="payments/cod_slips/%Y/%m/", null=True, blank=True)
    bank_reference = models.CharField(max_length=100, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    verified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="verified_cods")
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payments_cod_remittance"
        verbose_name = "COD Remittance"
        verbose_name_plural = "COD Remittances"

    def __str__(self) -> str:
        return f"COD {self.rider.user.name}: {self.amount} PKR ({self.status})"


class PayoutRequest(BaseModel):
    """Rider withdrawal request to transfer wallet earnings to bank / mobile wallet."""

    rider = models.ForeignKey(
        RiderProfile,
        on_delete=models.CASCADE,
        related_name="payout_requests",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payout_method = models.CharField(max_length=30, default="BANK_TRANSFER")
    account_title = models.CharField(max_length=150)
    account_number = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(max_length=20, choices=PayoutStatus.choices, default=PayoutStatus.PENDING, db_index=True)
    reference_number = models.CharField(max_length=100, blank=True, default="")
    rejection_reason = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_payouts")
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payments_payout_request"
        verbose_name = "Payout Request"
        verbose_name_plural = "Payout Requests"

    def __str__(self) -> str:
        return f"Payout {self.rider.user.name}: {self.amount} PKR ({self.status})"
