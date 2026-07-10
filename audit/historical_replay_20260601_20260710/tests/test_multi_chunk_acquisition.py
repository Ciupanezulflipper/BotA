from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from audit.historical_replay_20260601_20260710.src.multi_chunk_acquisition import (
    acquire_oanda_range,
)
from audit.historical_replay_20260601_20260710.src.request_metadata import (
    build_request_metadata,
)
from audit.historical_replay_20260601_20260710.src.response_metadata import (
    capture_response_metadata,
)
from audit.historical_replay_20260601_20260710.src.verify_run import verify_completed_run

UTC = timezone.utc


def _payload(start_minute: int, count: int) -> bytes:
    candles = []
    for offset in range(count):
        minute = start_minute + offset * 15
        hour, minute_of_hour = divmod(minute, 60)
        candles.append(
            {
                "complete": True,
                "volume": 10,
                "time": f"2026-06-01T{hour:02d}:{minute_of_hour:02d}:00Z",
                "mid": {"o": "1.1000", "h": "1.1010", "l": "1.0990", "c": "1.1005"},
            }
        )
    return json.dumps({"candles": candles}).encode("utf-8")


def test_pipeline_persists_reconciles_and_verifies(tmp_path):
    calls = []

    def fake_fetcher(**kwargs):
        calls.append(kwargs)
        body = _payload(0, 2)
        return {
            "request": build_request_metadata(
                method="GET",
                url="https://api-fxpractice.oanda.com" + kwargs["request_path_and_query"],
                headers={"Authorization": "Bearer secret"},
            ),
            "response": capture_response_metadata(
                200, {"Content-Type": "application/json", "RequestID": f"req-{len(calls)}"}
            ),
            "body": body,
        }

    result = acquire_oanda_range(
        output_root=tmp_path,
        run_id="range-001",
        instrument="EUR_USD",
        granularity="M15",
        start_utc=datetime(2026, 6, 1, 0, 0, tzinfo=UTC),
        end_utc=datetime(2026, 6, 1, 1, 0, tzinfo=UTC),
        token="explicit-token",
        enabled=False,
        fetcher=fake_fetcher,
    )

    assert result["chunk_count"] == 1
    assert result["reconciled_candle_count"] == 2
    assert calls[0]["enabled"] is False
    assert "count=" not in calls[0]["request_path_and_query"]

    manifest = json.loads((tmp_path / result["manifest_path"]).read_text())
    assert manifest["chunks"][0]["request_id"] == "req-1"
    assert manifest["reconciled_candle_count"] == 2
    assert "secret" not in (tmp_path / "metadata/range-001/chunk-0000.request.json").read_text()
    assert verify_completed_run(tmp_path, "range-001")["status"] == "PASS"


def test_pipeline_refuses_duplicate_run_id(tmp_path):
    def fake_fetcher(**kwargs):
        return {
            "request": build_request_metadata(method="GET", url="https://example.test", headers={}),
            "response": capture_response_metadata(200, {"Content-Type": "application/json"}),
            "body": _payload(0, 1),
        }

    params = dict(
        output_root=tmp_path,
        run_id="same-run",
        instrument="GBP_USD",
        granularity="M15",
        start_utc=datetime(2026, 6, 1, 0, 0, tzinfo=UTC),
        end_utc=datetime(2026, 6, 1, 0, 15, tzinfo=UTC),
        token="token",
        enabled=False,
        fetcher=fake_fetcher,
    )
    acquire_oanda_range(**params)
    with pytest.raises(FileExistsError):
        acquire_oanda_range(**params)


def test_pipeline_fails_on_conflicting_boundary_duplicates(tmp_path):
    bodies = [
        json.dumps({"candles": [{"complete": True, "volume": 1, "time": "2026-06-01T00:00:00Z", "mid": {"o": "1", "h": "1", "l": "1", "c": "1"}}]}).encode(),
        json.dumps({"candles": [{"complete": True, "volume": 1, "time": "2026-06-01T00:00:00Z", "mid": {"o": "2", "h": "2", "l": "2", "c": "2"}}]}).encode(),
    ]
    index = 0

    def fake_fetcher(**kwargs):
        nonlocal index
        body = bodies[index]
        index += 1
        return {
            "request": build_request_metadata(method="GET", url="https://example.test", headers={}),
            "response": capture_response_metadata(200, {"Content-Type": "application/json"}),
            "body": body,
        }

    with pytest.raises(ValueError, match="conflicting duplicate"):
        acquire_oanda_range(
            output_root=tmp_path,
            run_id="conflict",
            instrument="EUR_USD",
            granularity="M15",
            start_utc=datetime(2026, 6, 1, 0, 0, tzinfo=UTC),
            end_utc=datetime(2026, 7, 11, 0, 0, tzinfo=UTC),
            token="token",
            enabled=False,
            fetcher=fake_fetcher,
        )
