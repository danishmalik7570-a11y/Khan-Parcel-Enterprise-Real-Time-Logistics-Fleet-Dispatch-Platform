# =============================================================================
# Khan Parcel — Business Models
# =============================================================================

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import models

from apps.accounts.models import User
from apps.core.models import BaseModel


class BusinessProfile(BaseModel):
    """Corporate / Merchant business profile for bulk shipping."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="business_profile")
    company_name = models.CharField(max_length=200, db_index=True)
    ntn_number = models.CharField(max_length=50, blank=True, default="", help_text="National Tax Number")
    billing_address = models.TextField(blank=True, default="")
    contact_person = models.CharField(max_length=150, blank=True, default="")
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("50000.00"))
    is_verified = models.BooleanField(default=False)
    is_monthly_billing = models.BooleanField(default=False)

    class Meta:
        db_table = "business_profile"
        verbose_name = "Business Profile"
        verbose_name_plural = "Business Profiles"

    def __str__(self) -> str:
        return f"{self.company_name} ({self.user.name})"


class BulkBatchStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class BulkOrderBatch(BaseModel):
    """Batch container for bulk CSV order imports."""

    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name="batches")
    file = models.FileField(upload_to="business/bulk_csv/%Y/%m/")
    total_count = models.IntegerField(default=0)
    processed_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=BulkBatchStatus.choices, default=BulkBatchStatus.PENDING)
    error_log = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "business_bulk_batch"
        verbose_name = "Bulk Order Batch"
        verbose_name_plural = "Bulk Order Batches"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Batch #{self.id} for {self.business.company_name} ({self.status})"
