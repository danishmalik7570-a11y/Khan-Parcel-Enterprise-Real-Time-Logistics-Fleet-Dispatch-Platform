# =============================================================================
# Khan Parcel — ASGI Configuration
# =============================================================================
# Supports both HTTP (Django) and WebSocket (Channels) protocols.
# =============================================================================

from __future__ import annotations

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

from apps.realtime.middleware import JWTWebSocketMiddleware  # noqa: E402
from apps.realtime.routing import websocket_urlpatterns  # noqa: E402

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JWTWebSocketMiddleware(
                AuthMiddlewareStack(
                    URLRouter(websocket_urlpatterns)
                )
            )
        ),
    }
)
