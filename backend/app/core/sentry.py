from __future__ import annotations

import logging

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.types import Event, Hint

from app.core.logging_config import get_request_id

logger = logging.getLogger(__name__)


def _before_send(event: Event, hint: Hint) -> Event | None:
    """Attach the correlation id so Sentry events match structured logs."""
    request_id = get_request_id()
    if request_id:
        tags = event.setdefault("tags", {})
        tags["request_id"] = request_id
    return event


def init_sentry(*, dsn: str, environment: str, release: str | None = None) -> bool:
    """Initialize Sentry when a DSN is configured. No-op otherwise."""
    if not dsn.strip():
        return False

    sentry_sdk.init(
        dsn=dsn.strip(),
        environment=environment,
        release=release,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        before_send=_before_send,
        send_default_pii=False,
        traces_sample_rate=0.0,
    )
    logger.info("Sentry error tracking enabled", extra={"environment": environment})
    return True
