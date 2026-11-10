# =============================================================================
# Khan Parcel — Payments & Ledger Services
# =============================================================================

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import structlog
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.orders.models import Order, PaymentMethod, PaymentStatus
from apps.payments.models import (
    CODRemittance,
    CODStatus,
    EntryType,
    LedgerAccountType,
    LedgerEntry,
    PayoutRequest,
    PayoutStatus,
    Wallet,
)
from apps.riders.models import RiderProfile

logger = structlog.get_logger(__name__)

PLATFORM_COMMISSION_RATE = Decimal("0.20")  # 20% platform fee
RIDER_SHARE_RATE = Decimal("0.80")          # 80% to rider


class PaymentService:
    @staticmethod
    def get_or_create_wallet(user: User) -> Wallet:
        wallet, _ = Wallet.objects.get_or_create(user=user)
        return wallet

    @classmethod
    def settle_order_payment(cls, order: Order) -> None:
        """
        Executes complete double-entry settlement for a completed delivery order.
        """
        if not order.rider:
            logger.warning("settle_order_no_rider", order_id=str(order.id))
            return

        tx_id = uuid.uuid4()
        rider_user = order.rider.user
        customer_user = order.customer

        rider_wallet = cls.get_or_create_wallet(rider_user)
        customer_wallet = cls.get_or_create_wallet(customer_user)

        fare = order.fare_amount + order.surge_amount - order.discount_amount
        commission = (fare * PLATFORM_COMMISSION_RATE).quantize(Decimal("0.01"))
        rider_earnings = fare - commission
        cod_goods_amount = order.cod_amount

        with transaction.atomic():
            if order.payment_method == PaymentMethod.COD:
                # Cash on delivery: Rider receives all cash from recipient
                # Rider owes platform the commission fee
                rider_wallet.balance -= commission
                rider_wallet.save(update_fields=["balance", "updated_at"])

                # 1. Company commission earned
                LedgerEntry.objects.create(
                    transaction_id=tx_id,
                    order=order,
                    wallet=rider_wallet,
                    account_type=LedgerAccountType.COMPANY_COMMISSION,
                    entry_type=EntryType.CREDIT,
                    amount=commission,
                    balance_after=rider_wallet.balance,
                    description=f"Platform 20% commission on order {order.order_number}",
                )

                # 2. Rider wallet debited for commission
                LedgerEntry.objects.create(
                    transaction_id=tx_id,
                    order=order,
                    wallet=rider_wallet,
                    account_type=LedgerAccountType.RIDER_EARNINGS,
                    entry_type=EntryType.DEBIT,
                    amount=commission,
                    balance_after=rider_wallet.balance,
                    description=f"Deduction of platform fee on cash trip {order.order_number}",
                )

                # 3. If COD goods cash collected, record COD holding
                if cod_goods_amount > 0:
                    LedgerEntry.objects.create(
                        transaction_id=tx_id,
                        order=order,
                        wallet=rider_wallet,
                        account_type=LedgerAccountType.RIDER_COD_HOLDING,
                        entry_type=EntryType.CREDIT,
                        amount=cod_goods_amount,
                        balance_after=rider_wallet.balance,
                        description=f"COD merchant cash collected for order {order.order_number}",
                    )

            else:
                # Digital / Wallet / Prepaid: Customer prepaid fare
                # Credit rider wallet with 80% earnings
                rider_wallet.balance += rider_earnings
                rider_wallet.save(update_fields=["balance", "updated_at"])

                LedgerEntry.objects.create(
                    transaction_id=tx_id,
                    order=order,
                    wallet=rider_wallet,
                    account_type=LedgerAccountType.RIDER_EARNINGS,
                    entry_type=EntryType.CREDIT,
                    amount=rider_earnings,
                    balance_after=rider_wallet.balance,
                    description=f"80% trip payout for order {order.order_number}",
                )

                # Record company commission
                LedgerEntry.objects.create(
                    transaction_id=tx_id,
                    order=order,
                    wallet=None,
                    account_type=LedgerAccountType.COMPANY_COMMISSION,
                    entry_type=EntryType.CREDIT,
                    amount=commission,
                    balance_after=Decimal("0.00"),
                    description=f"Platform commission on order {order.order_number}",
                )

            # Update order payment status
            order.payment_status = PaymentStatus.PAID
            order.save(update_fields=["payment_status", "updated_at"])

            logger.info(
                "order_payment_settled",
                order_id=str(order.id),
                fare=str(fare),
                rider_earnings=str(rider_earnings),
                commission=str(commission),
            )

    @classmethod
    def topup_wallet(cls, user: User, amount: Decimal, payment_method: str, reference: str = "") -> Wallet:
        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")

        with transaction.atomic():
            wallet = cls.get_or_create_wallet(user)
            wallet.balance += amount
            wallet.save(update_fields=["balance", "updated_at"])

            LedgerEntry.objects.create(
                transaction_id=uuid.uuid4(),
                wallet=wallet,
                account_type=LedgerAccountType.CUSTOMER_WALLET,
                entry_type=EntryType.CREDIT,
                amount=amount,
                balance_after=wallet.balance,
                description=f"Wallet topup via {payment_method} (Ref: {reference})",
            )

        logger.info("wallet_topped_up", user_id=str(user.id), amount=str(amount))
        return wallet

    @classmethod
    def request_payout(
        cls,
        rider: RiderProfile,
        amount: Decimal,
        payout_method: str,
        account_title: str,
        account_number: str,
        bank_name: str = "",
    ) -> PayoutRequest:
        wallet = cls.get_or_create_wallet(rider.user)
        if wallet.is_frozen:
            raise ValueError("Wallet is frozen.")
        if amount > wallet.balance:
            raise ValueError(f"Insufficient balance. Available: {wallet.balance} PKR.")
        if amount < Decimal("500.00"):
            raise ValueError("Minimum payout request is 500 PKR.")

        with transaction.atomic():
            wallet.balance -= amount
            wallet.pending_balance += amount
            wallet.save(update_fields=["balance", "pending_balance", "updated_at"])

            req = PayoutRequest.objects.create(
                rider=rider,
                amount=amount,
                payout_method=payout_method,
                account_title=account_title,
                account_number=account_number,
                bank_name=bank_name,
                status=PayoutStatus.PENDING,
            )

        logger.info("payout_requested", rider_id=str(rider.id), amount=str(amount))
        return req

    @classmethod
    def process_payout(
        cls,
        payout_id: str,
        admin_user: User,
        approve: bool,
        reference_number: str = "",
        rejection_reason: str = "",
    ) -> PayoutRequest:
        with transaction.atomic():
            req = PayoutRequest.objects.select_for_update().get(id=payout_id)
            if req.status != PayoutStatus.PENDING:
                raise ValueError("Payout request has already been processed.")

            wallet = cls.get_or_create_wallet(req.rider.user)
            wallet.pending_balance = max(Decimal("0.00"), wallet.pending_balance - req.amount)

            if approve:
                req.status = PayoutStatus.PAID
                req.reference_number = reference_number
                req.reviewed_by = admin_user
                req.paid_at = timezone.now()
                wallet.save(update_fields=["pending_balance", "updated_at"])

                # Log withdrawal
                LedgerEntry.objects.create(
                    transaction_id=uuid.uuid4(),
                    wallet=wallet,
                    account_type=LedgerAccountType.RIDER_EARNINGS,
                    entry_type=EntryType.DEBIT,
                    amount=req.amount,
                    balance_after=wallet.balance,
                    description=f"Withdrawal payout completed (Ref: {reference_number})",
                )
            else:
                req.status = PayoutStatus.REJECTED
                req.rejection_reason = rejection_reason
                req.reviewed_by = admin_user
                # Refund back to wallet balance
                wallet.balance += req.amount
                wallet.save(update_fields=["balance", "pending_balance", "updated_at"])

            req.save()

        logger.info("payout_processed", payout_id=payout_id, approved=approve)
        return req

    @classmethod
    def submit_cod_remittance(
        cls,
        rider: RiderProfile,
        amount: Decimal,
        slip_image: Any,
        bank_ref: str = "",
        notes: str = "",
    ) -> CODRemittance:
        remittance = CODRemittance.objects.create(
            rider=rider,
            amount=amount,
            deposit_slip_image=slip_image,
            bank_reference=bank_ref,
            notes=notes,
            status=CODStatus.SUBMITTED,
        )
        logger.info("cod_remittance_submitted", rider_id=str(rider.id), amount=str(amount))
        return remittance

    @classmethod
    def verify_cod_remittance(cls, remittance_id: str, admin_user: User, approve: bool) -> CODRemittance:
        with transaction.atomic():
            rem = CODRemittance.objects.select_for_update().get(id=remittance_id)
            if rem.status != CODStatus.SUBMITTED:
                raise ValueError("Remittance is not pending verification.")

            rem.status = CODStatus.VERIFIED if approve else CODStatus.DISPUTED
            rem.verified_by = admin_user
            rem.verified_at = timezone.now()
            rem.save()

            if approve:
                # Relieve rider COD liability in ledger
                LedgerEntry.objects.create(
                    transaction_id=uuid.uuid4(),
                    wallet=cls.get_or_create_wallet(rem.rider.user),
                    account_type=LedgerAccountType.RIDER_COD_HOLDING,
                    entry_type=EntryType.DEBIT,
                    amount=rem.amount,
                    balance_after=Decimal("0.00"),
                    description=f"COD bank deposit verified by {admin_user.name} (Ref: {rem.bank_reference})",
                )

        logger.info("cod_remittance_verified", remittance_id=remittance_id, approved=approve)
        return rem
