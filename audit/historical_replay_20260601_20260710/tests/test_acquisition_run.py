from __future__ import annotations

import json
from pathlib import Path

import pytest

from audit.historical_replay_20260601_20260710.src.acquisition_run import (
    execute_synthetic_acquisition,
)


def sample_body() -> bytes:
    payload = {
        "instrument": "EUR_USD",
        "granularity": "M15",
        "candles": [
            {
                "complete": True,
                "volume": 12,
                "time": "2026-06-01T07:00:00.000000000Z",
                "mid": {"o": "1.1000", "h": "1.1010", "l": "1.0990", "c": "1.1005"},
            },
            {
                "complete": True,
                "volume": 15,
                "time": "2026-06-01T07:15:00.000000000Z",
                "mid": {"o": "1.1005", "h": "1.1020", "l": "1.1000", "c": "1.1015"},
            },
        ],
    }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def test_end_to_end_synthetic_acquisition(tmp_path: Path) -> None:
    result = execute_synthetic_acquisition(
        root=tmp_path,
        run_id="synthetic-001",
        request_url="https://api-fxpractice.oanda.com/v3/instruments/EUR_USD/candles?price=M&token=secret",
        request_headers={"Authorization": "Bearer secret", "Accept": "application/json"},
        response_status=200,
        response_headers={"Content-Type": "application/json", "RequestID": "abc-123", "Set-Cookie": "secret"},
        response_body=sample_body(),
    )

    assert result["candle_count"] == 2
    assert result["artifacts"]["artifact_count"] == 4

    manifest = json.loads((tmp_path / result["manifest_path"]).read_text())
    assert manifest["provider"] == "oanda"
    assert manifest["mode"] == "synthetic"
    assert manifest["request"]["headers"]["Authorization"] == "[REDACTED]"
    assert "secret" not in manifest["request"]["url"]
    assert manifest["response"]["headers"]["Set-Cookie"] == "[REDACTED]"
    assert manifest["response"]["request_id"] == "abc-123"

    parsed = json.loads((tmp_path / "derived/synthetic-001/candles.json").read_text())
    assert parsed[0]["time"] == "2026-06-01T07:00:00Z"
    assert parsed[1]["close"] == 1.1015


def test_run_is_write_once(tmp_path: Path) -> None:
    kwargs = dict(
        root=tmp_path,
        run_id="synthetic-002",
        request_url="https://api-fxpractice.oanda.com/v3/instruments/EUR_USD/candles?price=M",
        request_headers={},
        response_status=200,
        response_headers={"Content-Type": "application/json"},
        response_body=sample_body(),
    )
    execute_synthetic_acquisition(**kwargs)
    with pytest.raises(FileExistsError):
        execute_synthetic_acquisition(**kwargs)
