# =============================================================================
# Khan Parcel — Support Models
# =============================================================================

from __future__ import annotations

from typing import Any

from apps.core.gis_compat import gis_models
from django.db import models
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import BaseModel
from apps.orders.models import Order
from apps.riders.models import RiderProfile


class TicketPriority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    URGENT = "URGENT", "Urgent"


class TicketStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    RESOLVED = "RESOLVED", "Resolved"
    CLOSED = "CLOSED", "Closed"


class SupportTicket(BaseModel):
    """Customer or Rider support help ticket."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="support_tickets")
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL, related_name="support_tickets")
    subject = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=TicketPriority.choices, default=TicketPriority.MEDIUM)
    status = models.CharField(max_length=20, choices=TicketStatus.choices, default=TicketStatus.OPEN, db_index=True)
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_tickets")

    class Meta:
        db_table = "support_ticket"
        verbose_name = "Support Ticket"
        verbose_name_plural = "Support Tickets"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Ticket #{self.id}: {self.subject} ({self.status})"


class TicketMessage(BaseModel):
    """Discussion message on a support ticket."""

    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    attachment = models.FileField(upload_to="support/attachments/%Y/%m/", null=True, blank=True)

    class Meta:
        db_table = "support_ticket_message"
        ordering = ["created_at"]


class SOSAlert(BaseModel):
    """Emergency distress signal triggered by a rider in danger."""

    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name="sos_alerts")
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL, related_name="sos_alerts")
    location = gis_models.PointField(srid=4326, null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True, default="Accident or Security Incident")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="resolved_sos")

    class Meta:
        db_table = "support_sos_alert"
        verbose_name = "SOS Alert"
        verbose_name_plural = "SOS Alerts"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"SOS by {self.rider.user.name} ({'Resolved' if self.resolved_at else 'ACTIVE'})"
