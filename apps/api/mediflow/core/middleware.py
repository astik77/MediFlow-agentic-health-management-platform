"""
Security Headers ASGI Middleware (Phase 9).

Attaches defense-in-depth HTTP security headers to every API response and
enforces `Cache-Control: no-store` on `/api/v1/*` endpoints so private
patient medical records are never cached by browsers or intermediaries.
"""
from __future__ import annotations

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_STATIC_SECURITY_HEADERS: tuple[tuple[str, str], ...] = (
    ("x-content-type-options", "nosniff"),
    ("x-frame-options", "DENY"),
    ("referrer-policy", "strict-origin-when-cross-origin"),
    ("permissions-policy", "camera=(), microphone=(), geolocation=()"),
)


class SecurityHeadersMiddleware:
    """Pure ASGI middleware injecting hardened HTTP security headers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        is_api_route = path.startswith("/api/v1/")

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for key, value in _STATIC_SECURITY_HEADERS:
                    headers.setdefault(key, value)
                if is_api_route:
                    headers["cache-control"] = "no-store"
                    headers["pragma"] = "no-cache"
            await send(message)

        await self.app(scope, receive, send_with_headers)
