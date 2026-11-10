# =============================================================================
# Khan Parcel — Chat URLs
# =============================================================================

from __future__ import annotations

from django.urls import path

from apps.chat.views import OrderChatMessagesView

app_name = "chat"

urlpatterns = [
    path("orders/<uuid:order_id>/messages/", OrderChatMessagesView.as_view(), name="order-messages"),
]
