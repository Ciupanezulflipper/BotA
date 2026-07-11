from __future__ import annotations

import json
from pathlib import Path

import pytest

from audit.historical_replay_20260601_20260710.src.runtime_evidence import (
    load_runtime_evidence,
    parse_runtime_evidence,
)
from audit.historical_replay_20260601_20260710.src.runtime_epochs import RuntimeState


def valid_payload():
    return {
        "schema_version": 1,
        "window_start_utc": "2026-06-01T00:00:00Z",
        "window_end_utc": "2026-07-11T00:00:00Z",
        "source_commit": "fa289ad3f7b6ff430f13609950e5af341aee2e9d",
        "evidence_files": ["logs/cron.signals.log", "logs/run.log"],
        "epochs": [
            {
                "start_utc": "2026-06-01T00:00:00Z",
                "end_utc": "2026-06-02T00:00:00Z",
                "state": "UP",
                "evidence_id": "cron-log-001",
            },
            {
                "start_utc": "2026-06-02T00:00:00Z",
                "end_utc": "2026-06-03T00:00:00Z",
                "state": "UNKNOWN",
                "evidence_id": "gap-001",
            },
        ],
    }


def test_parses_explicit_epochs_without_filling_gaps():
    doc = parse_runtime_evidence(valid_payload())
    assert doc.schema_version == 1
    assert len(doc.epochs) == 2
    assert doc.epochs[0].state is RuntimeState.UP
    assert doc.epochs[1].state is RuntimeState.UNKNOWN
    assert doc.window_start_utc.isoformat() == "2026-06-01T00:00:00+00:00"


def test_allows_empty_epoch_list_but_requires_provenance():
    payload = valid_payload()
    payload["epochs"] = []
    doc = parse_runtime_evidence(payload)
    assert doc.epochs == ()

    payload = valid_payload()
    payload["evidence_files"] = []
    with pytest.raises(ValueError, match="evidence_files"):
        parse_runtime_evidence(payload)


def test_rejects_epoch_outside_window():
    payload = valid_payload()
    payload["epochs"][0]["start_utc"] = "2026-05-31T23:45:00Z"
    with pytest.raises(ValueError, match="outside"):
        parse_runtime_evidence(payload)


def test_rejects_overlap_duplicate_ids_and_unknown_state():
    payload = valid_payload()
    payload["epochs"][1]["start_utc"] = "2026-06-01T23:45:00Z"
    with pytest.raises(ValueError, match="overlap"):
        parse_runtime_evidence(payload)

    payload = valid_payload()
    payload["epochs"][1]["evidence_id"] = "cron-log-001"
    with pytest.raises(ValueError, match="unique"):
        parse_runtime_evidence(payload)

    payload = valid_payload()
    payload["epochs"][0]["state"] = "LIKELY_UP"
    with pytest.raises(ValueError, match="unsupported"):
        parse_runtime_evidence(payload)


def test_rejects_naive_time_and_unsupported_schema():
    payload = valid_payload()
    payload["window_start_utc"] = "2026-06-01T00:00:00"
    with pytest.raises(ValueError, match="timezone-aware"):
        parse_runtime_evidence(payload)

    payload = valid_payload()
    payload["schema_version"] = 2
    with pytest.raises(ValueError, match="schema_version"):
        parse_runtime_evidence(payload)


def test_loads_utf8_json_and_rejects_malformed_file(tmp_path: Path):
    path = tmp_path / "runtime.json"
    path.write_text(json.dumps(valid_payload()), encoding="utf-8")
    assert load_runtime_evidence(path).source_commit.startswith("fa289ad")

    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(ValueError, match="valid UTF-8 JSON"):
        load_runtime_evidence(path)
