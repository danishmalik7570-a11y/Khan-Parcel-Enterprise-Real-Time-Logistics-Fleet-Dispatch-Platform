# =============================================================================
# Khan Parcel — Core Base Models
# =============================================================================
# All domain models inherit from BaseModel for consistent UUID PKs,
# timestamps, and optional soft-delete.
# =============================================================================

from __future__ import annotations

import uuid
from typing import Any

from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """
    Abstract base model providing UUID primary key and timestamps.

    All domain models should inherit from this class.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier (UUID v4).",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when this record was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when this record was last updated.",
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.pk}>"


class SoftDeleteManager(models.Manager["SoftDeleteModel"]):
    """Manager that filters out soft-deleted records by default."""

    def get_queryset(self) -> models.QuerySet[SoftDeleteModel]:
        return super().get_queryset().filter(deleted_at__isnull=True)

    def all_with_deleted(self) -> models.QuerySet[SoftDeleteModel]:
        """Return all records including soft-deleted ones."""
        return super().get_queryset()

    def deleted_only(self) -> models.QuerySet[SoftDeleteModel]:
        """Return only soft-deleted records."""
        return super().get_queryset().filter(deleted_at__isnull=False)


class SoftDeleteModel(BaseModel):
    """
    Abstract model with soft-delete support.

    Records are never actually deleted from the database — they are
    marked with a `deleted_at` timestamp and filtered from default queries.
    """

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp when this record was soft-deleted (null = active).",
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta(BaseModel.Meta):
        abstract = True

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self, **kwargs: Any) -> None:
        """Mark this record as deleted without removing it from the database."""
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.deleted_at = None
        self.save(update_fields=["deleted_at", "updated_at"])

    def delete(self, using: Any = None, keep_parents: bool = False) -> tuple[int, dict[str, int]]:
        """Override delete to perform soft-delete by default."""
        self.soft_delete()
        return (1, {f"{self._meta.label}": 1})


class MoneyField(models.BigIntegerField):
    """
    Money stored as minor units (paisa / cents).

    Always store money as integers to avoid floating point issues.
    Pair with a `currency` CharField on the parent model.
    """

    description = "Money amount in minor units (e.g., paisa)"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("default", 0)
        kwargs.setdefault("help_text", "Amount in minor units (paisa/cents).")
        super().__init__(*args, **kwargs)
