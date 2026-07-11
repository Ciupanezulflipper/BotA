from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .acquisition_run import execute_synthetic_acquisition
from .verify_run import verify_completed_run


def _synthetic_payload() -> bytes:
    payload = {
        "instrument": "EUR_USD",
        "granularity": "M15",
        "candles": [
            {
                "complete": True,
                "volume": 101,
                "time": "2026-06-01T07:00:00.000000000Z",
                "mid": {"o": "1.10000", "h": "1.10100", "l": "1.09950", "c": "1.10050"},
            },
            {
                "complete": True,
                "volume": 99,
                "time": "2026-06-01T07:15:00.000000000Z",
                "mid": {"o": "1.10050", "h": "1.10120", "l": "1.10010", "c": "1.10090"},
            },
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def run_synthetic_proof(root: Path) -> dict[str, Any]:
    """Create, verify, tamper with a copy, and prove tamper detection."""
    root = root.resolve()
    run_id = "synthetic-proof"

    acquisition = execute_synthetic_acquisition(
        root=root,
        run_id=run_id,
        request_url=(
            "https://api-fxpractice.oanda.com/v3/instruments/EUR_USD/candles"
            "?price=M&granularity=M15&from=2026-06-01T07%3A00%3A00Z"
            "&to=2026-06-01T07%3A30%3A00Z&token=secret"
        ),
        request_headers={"Authorization": "Bearer secret", "Accept": "application/json"},
        response_status=200,
        response_headers={
            "Content-Type": "application/json",
            "RequestID": "synthetic-request-id",
            "Set-Cookie": "secret-cookie",
        },
        response_body=_synthetic_payload(),
    )
    verified = verify_completed_run(root, run_id)

    tamper_root = root.parent / f"{root.name}-tampered"
    if tamper_root.exists():
        shutil.rmtree(tamper_root)
    shutil.copytree(root, tamper_root)
    tampered_raw = tamper_root / "raw" / run_id / "response.json"
    tampered_raw.write_bytes(tampered_raw.read_bytes() + b"\nTAMPERED")

    tamper_detected = False
    tamper_error = ""
    try:
        verify_completed_run(tamper_root, run_id)
    except (ValueError, FileNotFoundError) as exc:
        tamper_detected = True
        tamper_error = str(exc)

    status = "PASS" if verified.get("status") == "PASS" and tamper_detected else "FAIL"
    return {
        "status": status,
        "run_id": run_id,
        "acquisition": acquisition,
        "verification": verified,
        "tamper_detection": {
            "detected": tamper_detected,
            "error": tamper_error,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run synthetic historical-replay integrity proof")
    parser.add_argument("--root", default="", help="Optional output root; defaults to a temporary directory")
    args = parser.parse_args()

    if args.root:
        root = Path(args.root)
        root.mkdir(parents=True, exist_ok=False)
        report = run_synthetic_proof(root)
    else:
        with tempfile.TemporaryDirectory(prefix="bota-replay-proof-") as tmp:
            report = run_synthetic_proof(Path(tmp) / "run")

    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
