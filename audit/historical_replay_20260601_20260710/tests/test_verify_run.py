import json
from pathlib import Path

import pytest

from audit.historical_replay_20260601_20260710.src.acquisition_run import execute_synthetic_acquisition
from audit.historical_replay_20260601_20260710.src.verify_run import verify_completed_run


def _payload() -> bytes:
    return json.dumps(
        {
            "instrument": "EUR_USD",
            "granularity": "M15",
            "candles": [
                {
                    "complete": True,
                    "volume": 10,
                    "time": "2026-06-01T07:00:00.000000000Z",
                    "mid": {"o": "1.1000", "h": "1.1010", "l": "1.0990", "c": "1.1005"},
                }
            ],
        }
    ).encode("utf-8")


def _run(root: Path, run_id: str = "synthetic-verify") -> None:
    execute_synthetic_acquisition(
        root=root,
        run_id=run_id,
        request_url="https://api-fxpractice.oanda.com/v3/instruments/EUR_USD/candles?granularity=M15&price=M&token=secret",
        request_headers={"Authorization": "Bearer secret", "Accept": "application/json"},
        response_status=200,
        response_headers={"Content-Type": "application/json", "RequestID": "req-123"},
        response_body=_payload(),
    )


def test_verify_completed_run_passes(tmp_path: Path) -> None:
    _run(tmp_path)
    result = verify_completed_run(tmp_path, "synthetic-verify")
    assert result["status"] == "PASS"
    assert result["artifact_count"] == 4
    assert "raw/synthetic-verify/response.json" in result["verified_artifacts"]


def test_verify_detects_artifact_tamper(tmp_path: Path) -> None:
    _run(tmp_path)
    raw = tmp_path / "raw" / "synthetic-verify" / "response.json"
    raw.write_bytes(raw.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="artifact (size|sha256) mismatch"):
        verify_completed_run(tmp_path, "synthetic-verify")


def test_verify_detects_index_tamper(tmp_path: Path) -> None:
    _run(tmp_path)
    manifest_path = tmp_path / "manifests" / "synthetic-verify.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"]["artifacts"][0]["bytes"] += 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="artifact index hash mismatch"):
        verify_completed_run(tmp_path, "synthetic-verify")


def test_verify_detects_missing_artifact(tmp_path: Path) -> None:
    _run(tmp_path)
    (tmp_path / "metadata" / "synthetic-verify" / "request.json").unlink()
    with pytest.raises(FileNotFoundError, match="artifact missing"):
        verify_completed_run(tmp_path, "synthetic-verify")
