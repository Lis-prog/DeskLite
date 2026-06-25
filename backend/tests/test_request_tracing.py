from __future__ import annotations

import json
import logging

import tests.bootstrap_env  # noqa: F401  # must run before app imports
from app.core.logging_config import (
    JsonLogFormatter,
    RequestIdFilter,
    configure_logging,
    request_id_ctx,
)
from app.core.request_tracing import REQUEST_ID_HEADER, _normalize_request_id


def test_response_includes_generated_request_id(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    request_id = res.headers.get(REQUEST_ID_HEADER)
    assert request_id
    assert len(request_id) == 32  # uuid4().hex


def test_inbound_request_id_is_echoed_back(client):
    res = client.get("/api/v1/health", headers={REQUEST_ID_HEADER: "trace-abc-123"})
    assert res.headers.get(REQUEST_ID_HEADER) == "trace-abc-123"


def test_each_request_gets_a_distinct_id(client):
    first = client.get("/api/v1/health").headers[REQUEST_ID_HEADER]
    second = client.get("/api/v1/health").headers[REQUEST_ID_HEADER]
    assert first != second


def test_request_id_contextvar_is_reset_after_request(client):
    client.get("/api/v1/health")
    assert request_id_ctx.get() is None


def test_normalize_request_id_generates_when_missing():
    assert len(_normalize_request_id(None)) == 32
    assert len(_normalize_request_id("   ")) == 32


def test_normalize_request_id_rejects_overlong_value():
    overlong = "x" * 500
    assert _normalize_request_id(overlong) != overlong
    assert len(_normalize_request_id(overlong)) == 32


def test_normalize_request_id_keeps_valid_value():
    assert _normalize_request_id("abc-123") == "abc-123"


def test_json_formatter_includes_correlation_id_and_extras():
    record = logging.LogRecord(
        name="desklite.request",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request.finish",
        args=(),
        exc_info=None,
    )
    RequestIdFilter().filter(record)
    record.status_code = 200
    record.request_id = "trace-xyz"

    payload = json.loads(JsonLogFormatter().format(record))
    assert payload["message"] == "request.finish"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "desklite.request"
    assert payload["request_id"] == "trace-xyz"
    assert payload["status_code"] == 200


def test_json_formatter_serializes_exception():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = logging.LogRecord(
            name="desklite.request",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="request.error",
            args=(),
            exc_info=sys.exc_info(),
        )
    payload = json.loads(JsonLogFormatter().format(record))
    assert "ValueError: boom" in payload["exception"]


def test_configure_logging_installs_single_handler():
    configure_logging(level="DEBUG", json_logs=True)
    root = logging.getLogger()
    try:
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0].formatter, JsonLogFormatter)
        assert root.level == logging.DEBUG
    finally:
        # Restore the app's default logging configuration for other tests.
        configure_logging(level="INFO", json_logs=False)
