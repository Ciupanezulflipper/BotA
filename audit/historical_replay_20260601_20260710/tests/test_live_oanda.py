from pathlib import Path

import pytest

from audit.historical_replay_20260601_20260710.src.live_oanda import (
    OANDA_PRACTICE_BASE,
    TransportResponse,
    fetch_oanda_chunk,
)


def test_live_fetch_is_disabled_by_default(tmp_path: Path):
    with pytest.raises(PermissionError):
        fetch_oanda_chunk(
            output_root=tmp_path,
            request_path_and_query="/v3/instruments/EUR_USD/candles?from=a&to=b&granularity=M15&price=M",
            token="secret",
        )


def test_live_fetch_requires_token(tmp_path: Path):
    with pytest.raises(ValueError, match="token"):
        fetch_oanda_chunk(
            output_root=tmp_path,
            request_path_and_query="/v3/instruments/EUR_USD/candles?from=a&to=b&granularity=M15&price=M",
            token="",
            enabled=True,
        )


def test_live_fetch_rejects_unapproved_host(tmp_path: Path):
    with pytest.raises(ValueError, match="base URL"):
        fetch_oanda_chunk(
            output_root=tmp_path,
            request_path_and_query="/v3/instruments/EUR_USD/candles?from=a&to=b&granularity=M15&price=M",
            token="secret",
            enabled=True,
            base_url="https://example.com",
        )


def test_live_fetch_rejects_count(tmp_path: Path):
    with pytest.raises(ValueError, match="count"):
        fetch_oanda_chunk(
            output_root=tmp_path,
            request_path_and_query="/v3/instruments/EUR_USD/candles?count=10&granularity=M15&price=M",
            token="secret",
            enabled=True,
        )


def test_live_fetch_redacts_token_and_returns_raw_bytes(tmp_path: Path):
    observed = {}

    def fake_transport(url, headers, timeout_seconds):
        observed["url"] = url
        observed["authorization"] = headers["Authorization"]
        observed["timeout"] = timeout_seconds
        return TransportResponse(
            status=200,
            headers={"Content-Type": "application/json", "RequestID": "rid-1"},
            body=b'{"candles":[]}',
        )

    result = fetch_oanda_chunk(
        output_root=tmp_path,
        request_path_and_query="/v3/instruments/EUR_USD/candles?from=a&to=b&granularity=M15&price=M",
        token="top-secret",
        enabled=True,
        transport=fake_transport,
    )

    assert observed["url"].startswith(OANDA_PRACTICE_BASE)
    assert observed["authorization"] == "Bearer top-secret"
    assert result["request"].headers["Authorization"] == "[REDACTED]"
    assert result["response"].request_id == "rid-1"
    assert result["body"] == b'{"candles":[]}'


def test_live_fetch_fails_closed_on_http_error(tmp_path: Path):
    def fake_transport(url, headers, timeout_seconds):
        return TransportResponse(status=401, headers={}, body=b'{"errorMessage":"unauthorized"}')

    with pytest.raises(RuntimeError, match="HTTP 401"):
        fetch_oanda_chunk(
            output_root=tmp_path,
            request_path_and_query="/v3/instruments/EUR_USD/candles?from=a&to=b&granularity=M15&price=M",
            token="bad-token",
            enabled=True,
            transport=fake_transport,
        )


def test_live_fetch_rejects_non_json_payload(tmp_path: Path):
    def fake_transport(url, headers, timeout_seconds):
        return TransportResponse(status=200, headers={}, body=b"not-json")

    with pytest.raises(ValueError, match="valid UTF-8 JSON"):
        fetch_oanda_chunk(
            output_root=tmp_path,
            request_path_and_query="/v3/instruments/EUR_USD/candles?from=a&to=b&granularity=M15&price=M",
            token="secret",
            enabled=True,
            transport=fake_transport,
        )
