from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from audit.historical_acquisition_20260807.acquire import (
    DEFAULT_GRANULARITIES,
    DEFAULT_INSTRUMENTS,
    EXECUTION_PHRASE,
    TransportResponse,
    build_preview,
    execute_acquisition,
    plan_requests,
    verify_manifest,
    write_once,
)

START = datetime(2026, 6, 1, tzinfo=timezone.utc)
END = datetime(2026, 7, 11, tzinfo=timezone.utc)


def _payload(start: str) -> bytes:
    return json.dumps(
        {
            "candles": [
                {
                    "complete": True,
                    "volume": 100,
                    "time": start,
                    "mid": {"o": "1.1000", "h": "1.1010", "l": "1.0990", "c": "1.1005"},
                }
            ]
        }
    ).encode()


def test_preview_is_no_network_and_uses_explicit_from_to(tmp_path):
    preview = build_preview(
        start_utc=START,
        end_utc=END,
        output_root=tmp_path / "out",
        run_id="r1",
    )
    assert preview["mode"] == "dry_run_no_network"
    assert preview["network_permitted"] is False
    assert preview["instruments"] == list(DEFAULT_INSTRUMENTS)
    assert preview["granularities"] == list(DEFAULT_GRANULARITIES)
    assert preview["request_count"] == 8
    assert all("from=" in row["path_and_query"] for row in preview["requests"])
    assert all("to=" in row["path_and_query"] for row in preview["requests"])
    assert all("count=" not in row["path_and_query"] for row in preview["requests"])
    assert preview["plan_sha256"]


def test_chunking_is_bounded_and_deterministic():
    requests = plan_requests(
        start_utc=START,
        end_utc=END,
        instruments=("EUR_USD",),
        granularities=("M15",),
        max_candles=1000,
    )
    assert len(requests) > 1
    assert requests[0].start_utc == "2026-06-01T00:00:00Z"
    assert requests[-1].end_utc == "2026-07-11T00:00:00Z"
    assert all("count=" not in row.path_and_query for row in requests)


def test_write_once_rejects_overwrite(tmp_path):
    root = tmp_path / "out"
    write_once(root, "a/file.txt", b"one")
    with pytest.raises(FileExistsError):
        write_once(root, "a/file.txt", b"two")


def test_execute_requires_phrase_and_token(tmp_path):
    outside = tmp_path / "outside"
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(PermissionError):
        execute_acquisition(
            output_root=outside,
            run_id="r",
            start_utc=START,
            end_utc=END,
            token="secret",
            authorization_phrase="wrong",
            repository_root=repo,
        )
    with pytest.raises(PermissionError):
        execute_acquisition(
            output_root=outside,
            run_id="r",
            start_utc=START,
            end_utc=END,
            token="",
            authorization_phrase=EXECUTION_PHRASE,
            repository_root=repo,
        )


def test_execute_rejects_output_inside_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(ValueError, match="outside"):
        execute_acquisition(
            output_root=repo / "audit-output",
            run_id="r",
            start_utc=START,
            end_utc=END,
            token="secret",
            authorization_phrase=EXECUTION_PHRASE,
            repository_root=repo,
            transport=lambda *_: TransportResponse(200, {}, _payload("2026-06-01T00:00:00.000000000Z")),
        )


def test_execute_persists_redacted_immutable_artifacts_and_verifies(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    output = tmp_path / "dataset"
    calls = []

    def fake_transport(host, path, headers, timeout):
        calls.append((host, path, dict(headers), timeout))
        return TransportResponse(
            200,
            {"Content-Type": "application/json", "RequestID": "rid-1", "X-Secret": "drop-me"},
            _payload("2026-06-02T12:00:00.000000000Z"),
        )

    result = execute_acquisition(
        output_root=output,
        run_id="r1",
        start_utc=START,
        end_utc=END,
        token="super-secret-token",
        authorization_phrase=EXECUTION_PHRASE,
        repository_root=repo,
        transport=fake_transport,
    )

    assert result["status"] == "PASS"
    assert result["request_count"] == 8
    assert result["series_count"] == 8
    assert len(calls) == 8
    assert all(call[2]["Authorization"] == "Bearer super-secret-token" for call in calls)

    all_bytes = b"".join(path.read_bytes() for path in output.rglob("*") if path.is_file())
    assert b"super-secret-token" not in all_bytes
    assert b"X-Secret" not in all_bytes

    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["token_persisted"] is False
    assert len(manifest["series"]) == 8
    assert len(manifest["artifacts"]) == 33
    assert verify_manifest(output)["status"] == "PASS"

    first_csv = output / "canonical/EUR_USD_M15.csv"
    assert first_csv.read_text().splitlines()[0] == "time,open,high,low,close,volume,complete"

    with pytest.raises(FileExistsError):
        execute_acquisition(
            output_root=output,
            run_id="r1",
            start_utc=START,
            end_utc=END,
            token="super-secret-token",
            authorization_phrase=EXECUTION_PHRASE,
            repository_root=repo,
            transport=fake_transport,
        )


def test_verify_detects_tamper(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    output = tmp_path / "dataset"

    def fake_transport(*_):
        return TransportResponse(200, {}, _payload("2026-06-02T12:00:00.000000000Z"))

    execute_acquisition(
        output_root=output,
        run_id="r1",
        start_utc=START,
        end_utc=END,
        token="secret",
        authorization_phrase=EXECUTION_PHRASE,
        repository_root=repo,
        transport=fake_transport,
    )
    target = output / "canonical/EUR_USD_M15.csv"
    target.write_text(target.read_text() + "tamper\n")
    verification = verify_manifest(output)
    assert verification["status"] == "FAIL"
    assert any(item.startswith(("size:", "sha256:")) for item in verification["failures"])
