from __future__ import annotations

import json
from pathlib import Path

from audit.historical_replay_20260601_20260710.src.proof_runner import run_synthetic_proof


def test_synthetic_proof_passes_and_detects_tampering(tmp_path: Path) -> None:
    root = tmp_path / "proof"
    report = run_synthetic_proof(root)

    assert report["status"] == "PASS"
    assert report["verification"]["status"] == "PASS"
    assert report["verification"]["artifact_count"] == 4
    assert report["tamper_detection"]["detected"] is True
    assert "mismatch" in report["tamper_detection"]["error"]

    manifest = json.loads((root / "manifests" / "synthetic-proof.json").read_text(encoding="utf-8"))
    assert manifest["request"]["headers"]["Authorization"] == "[REDACTED]"
    assert "secret" not in manifest["request"]["url"]
    assert manifest["response"]["headers"]["Set-Cookie"] == "[REDACTED]"
    assert manifest["response"]["request_id"] == "synthetic-request-id"
