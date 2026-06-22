from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

HSTS_MAX_AGE = 31_536_000  # 1 year


def build_security_headers(*, enable_hsts: bool) -> dict[str, str]:
    """Return standard hardening headers for HTTP responses."""
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }
    if enable_hsts:
        headers["Strict-Transport-Security"] = f"max-age={HSTS_MAX_AGE}; includeSubDomains"
    return headers


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach security headers to every API response."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        enable_hsts = settings.app_env.lower() == "production"
        for name, value in build_security_headers(enable_hsts=enable_hsts).items():
            response.headers.setdefault(name, value)
        return response
