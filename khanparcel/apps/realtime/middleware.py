# =============================================================================
# Khan Parcel — Realtime JWT WebSocket Middleware
# =============================================================================

from __future__ import annotations

import urllib.parse
from typing import Any, Callable

import jwt
import structlog
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth.models import AnonymousUser

from apps.accounts.models import User

logger = structlog.get_logger(__name__)


@database_sync_to_async
def get_user_from_token(token_str: str) -> User | AnonymousUser:
    try:
        # Decode JWT token
        payload = jwt.decode(
            token_str,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        user_id = payload.get("user_id")
        if not user_id:
            return AnonymousUser()
        return User.objects.get(id=user_id, is_active=True)
    except Exception as e:
        logger.debug("ws_jwt_auth_failed", error=str(e))
        return AnonymousUser()


class JWTWebSocketMiddleware:
    """
    Custom Channels middleware to authenticate WebSockets using JWT in query param or headers.
    """

    def __init__(self, inner: Callable[[dict[str, Any], Callable, Callable], Any]) -> None:
        self.inner = inner

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> Any:
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = urllib.parse.parse_qs(query_string)
        token_list = query_params.get("token")

        token = None
        if token_list:
            token = token_list[0]
        else:
            # Check headers
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode("utf-8")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if token:
            scope["user"] = await get_user_from_token(token)
        else:
            scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)
