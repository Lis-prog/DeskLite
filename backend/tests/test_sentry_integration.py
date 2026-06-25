from __future__ import annotations

from unittest.mock import patch

import pytest

from app.core.logging_config import request_id_ctx
from app.core.sentry import _before_send, init_sentry

pytestmark = pytest.mark.unit


def test_init_sentry_noop_without_dsn():
    with patch("app.core.sentry.sentry_sdk.init") as mock_init:
        assert init_sentry(dsn="", environment="development") is False
        mock_init.assert_not_called()


def test_init_sentry_configures_sdk_when_dsn_set():
    with patch("app.core.sentry.sentry_sdk.init") as mock_init:
        assert (
            init_sentry(
                dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
                environment="production",
                release="desklite-backend@0.1.0",
            )
            is True
        )
        mock_init.assert_called_once()
        kwargs = mock_init.call_args.kwargs
        assert kwargs["dsn"] == "https://examplePublicKey@o0.ingest.sentry.io/0"
        assert kwargs["environment"] == "production"
        assert kwargs["release"] == "desklite-backend@0.1.0"
        assert kwargs["send_default_pii"] is False
        assert kwargs["before_send"] is _before_send


def test_before_send_attaches_request_id():
    token = request_id_ctx.set("corr-abc-123")
    try:
        event: dict = {}
        result = _before_send(event, {})
        assert result is event
        assert result["tags"]["request_id"] == "corr-abc-123"
    finally:
        request_id_ctx.reset(token)


def test_before_send_leaves_event_unchanged_without_request_id():
    event: dict = {"message": "standalone error"}
    result = _before_send(event, {})
    assert result == {"message": "standalone error"}
