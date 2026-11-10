# =============================================================================
# Khan Parcel — Chat Models
# =============================================================================

from __future__ import annotations

from typing import Any

from django.db import models

from apps.accounts.models import User
from apps.core.models import BaseModel
from apps.orders.models import Order


class ChatMessage(BaseModel):
    """Direct message between customer and rider on an active order."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="chat_messages",
        db_index=True,
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    text = models.TextField(blank=True, default="")
    attachment = models.FileField(upload_to="chat/attachments/%Y/%m/", null=True, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "chat_message"
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Msg {self.id} on {self.order.order_number} by {self.sender.name}: {self.text[:30]}"
