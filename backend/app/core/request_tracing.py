from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging_config import request_id_ctx

REQUEST_ID_HEADER = "X-Request-ID"
# Cap inbound ids so a client can't smuggle huge/garbage values into our logs.
_MAX_REQUEST_ID_LENGTH = 128

logger = logging.getLogger("desklite.request")


def _normalize_request_id(value: str | None) -> str:
    """Reuse a sane client-supplied request id, otherwise mint a new one."""
    if value:
        candidate = value.strip()
        if 0 < len(candidate) <= _MAX_REQUEST_ID_LENGTH:
            return candidate
    return uuid.uuid4().hex


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Assign a correlation id to each request and emit structured access logs.

    The id is taken from the inbound ``X-Request-ID`` header when present so a
    trace can span the proxy/frontend and backend, or generated otherwise. It is
    bound to a contextvar for the duration of the request (so all log lines carry
    it) and echoed back on the response header.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = _normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
        token = request_id_ctx.set(request_id)
        start = time.perf_counter()

        client_host = request.client.host if request.client else None
        logger.info(
            "request.start",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client": client_host,
            },
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "request.error",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            request_id_ctx.reset(token)
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request.finish",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        response.headers[REQUEST_ID_HEADER] = request_id
        request_id_ctx.reset(token)
        return response
