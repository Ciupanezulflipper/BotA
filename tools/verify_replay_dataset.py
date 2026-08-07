#!/usr/bin/env python3
"""Verify one immutable BotA replay candle dataset without network access."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ALLOWED_PAIRS = {"EURUSD", "GBPUSD"}
ALLOWED_TIMEFRAMES = {"M15", "H1", "H4", "D1"}
CSV_HEADER = ["time", "open", "high", "low", "close"]


def parse_utc(value: str) -> datetime:
    """Parse an aware ISO-8601 timestamp and normalize it to UTC."""
    text = str(value).strip()
    if not text:
        raise ValueError("timestamp is empty")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def iso_z(value: datetime) -> str:
    """Render an aware timestamp in canonical UTC Z form."""
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_pair(value: str) -> str:
    """Normalize and validate a replay pair."""
    pair = str(value).replace("/", "").replace("_", "").replace(" ", "").upper()
    if pair not in ALLOWED_PAIRS:
        raise ValueError(f"unsupported pair: {value}")
    return pair


def normalize_tf(value: str) -> str:
    """Normalize and validate a replay timeframe."""
    tf = str(value).strip().upper()
    if tf == "1D":
        tf = "D1"
    if tf not in ALLOWED_TIMEFRAMES:
        raise ValueError(f"unsupported timeframe: {value}")
    return tf


def _safe_artifact_path(dataset_root: Path, relative: str) -> Path:
    """Resolve one manifest artifact and prove it stays inside the dataset."""
    if not relative or Path(relative).is_absolute():
        raise ValueError(f"invalid artifact path: {relative}")
    root = dataset_root.resolve()
    path = (root / relative).resolve()
    if os.path.commonpath([str(root), str(path)]) != str(root):
        raise ValueError(f"artifact escapes dataset root: {relative}")
    return path


def _file_sha256(path: Path) -> str:
    """Hash one file without loading the entire artifact into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _finite_positive(value: str, field: str, line_no: int) -> float:
    """Parse one finite positive OHLC value."""
    try:
        number = float(value)
    except Exception as exc:
        raise ValueError(f"line {line_no}: invalid {field}") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"line {line_no}: invalid {field}")
    return number


def _parse_candle_row(
    row: dict[str, str],
    *,
    line_no: int,
    raw_start: datetime,
    raw_end: datetime,
) -> datetime:
    """Validate one canonical candle CSV row and return its UTC timestamp."""
    try:
        stamp = datetime.strptime(row["time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception as exc:
        raise ValueError(f"line {line_no}: invalid timestamp") from exc

    opened = _finite_positive(row["open"], "open", line_no)
    high = _finite_positive(row["high"], "high", line_no)
    low = _finite_positive(row["low"], "low", line_no)
    close = _finite_positive(row["close"], "close", line_no)

    if high < max(opened, close) or low > min(opened, close) or low > high:
        raise ValueError(f"line {line_no}: invalid OHLC ordering")
    if stamp < raw_start or stamp >= raw_end:
        raise ValueError(f"line {line_no}: timestamp outside raw range")
    return stamp


def verify_csv(
    path: Path,
    *,
    raw_start: datetime,
    raw_end: datetime,
    evaluation_start: datetime,
    min_warmup_bars: int,
) -> dict[str, object]:
    """Verify one canonical candle CSV and its replay warm-up coverage."""
    rows: list[datetime] = []

    with path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != CSV_HEADER:
            raise ValueError(f"unexpected CSV header in {path.name}")
        for line_no, row in enumerate(reader, start=2):
            rows.append(
                _parse_candle_row(
                    row,
                    line_no=line_no,
                    raw_start=raw_start,
                    raw_end=raw_end,
                )
            )

    if not rows:
        raise ValueError("CSV contains no candles")
    if any(left >= right for left, right in zip(rows, rows[1:])):
        raise ValueError("timestamps are not strictly increasing")

    pre_evaluation = sum(stamp < evaluation_start for stamp in rows)
    evaluation_rows = sum(evaluation_start <= stamp < raw_end for stamp in rows)
    if pre_evaluation < min_warmup_bars:
        raise ValueError(f"insufficient warm-up candles: {pre_evaluation} < {min_warmup_bars}")
    if evaluation_rows <= 0:
        raise ValueError("no candles in evaluation range")

    return {
        "rows": len(rows),
        "pre_evaluation_rows": pre_evaluation,
        "evaluation_rows": evaluation_rows,
        "first_time": iso_z(rows[0]),
        "last_time": iso_z(rows[-1]),
    }


def _load_manifest(dataset_root: Path, expected_dataset_id: str) -> tuple[Path, dict[str, object]]:
    """Load the terminal manifest and reject failed or incomplete datasets."""
    root = dataset_root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"dataset root missing: {root}")
    if (root / "FAILED.json").exists():
        raise ValueError("FAILED.json exists; dataset is not replay-eligible")

    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("manifest.json missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")
    if manifest.get("status") != "COMPLETE":
        raise ValueError("manifest status is not COMPLETE")
    if manifest.get("dataset_id") != expected_dataset_id:
        raise ValueError("dataset id mismatch")
    if manifest.get("provider") != "oanda" or manifest.get("price_component") != "M":
        raise ValueError("provider/price contract mismatch")
    if manifest.get("production_cache_touched") is not False:
        raise ValueError("manifest does not prove production cache isolation")
    return root, manifest


def _expected_scope(pairs: list[str], timeframes: list[str]) -> tuple[list[str], list[str], set[tuple[str, str]]]:
    """Normalize requested scope and return the exact expected stream set."""
    requested_pairs = list(dict.fromkeys(normalize_pair(pair) for pair in pairs))
    requested_tfs = list(dict.fromkeys(normalize_tf(tf) for tf in timeframes))
    expected_streams = {(pair, tf) for pair in requested_pairs for tf in requested_tfs}
    if not expected_streams:
        raise ValueError("at least one pair and timeframe are required")
    return requested_pairs, requested_tfs, expected_streams


def _validate_manifest_scope_and_range(
    manifest: dict[str, object],
    *,
    raw_start: datetime,
    raw_end: datetime,
    evaluation_start: datetime,
    requested_pairs: list[str],
    requested_tfs: list[str],
    min_warmup_bars: int,
) -> None:
    """Validate manifest scope plus raw/evaluation boundaries."""
    if set(manifest.get("pairs", [])) != set(requested_pairs):
        raise ValueError("pair scope mismatch")
    if set(manifest.get("timeframes", [])) != set(requested_tfs):
        raise ValueError("timeframe scope mismatch")

    range_info = manifest.get("range")
    if not isinstance(range_info, dict):
        raise ValueError("manifest range missing")
    if range_info.get("start_utc") != iso_z(raw_start):
        raise ValueError("raw start mismatch")
    if range_info.get("end_utc_exclusive") != iso_z(raw_end):
        raise ValueError("raw end mismatch")
    if not raw_start < evaluation_start < raw_end:
        raise ValueError("evaluation start must be inside raw range")
    if min_warmup_bars < 1:
        raise ValueError("min warm-up bars must be positive")


def _verify_artifact_record(root: Path, record: object) -> str:
    """Verify one manifest artifact and return its relative path."""
    if not isinstance(record, dict):
        raise ValueError("artifact record is not an object")
    relative = str(record.get("path", ""))
    path = _safe_artifact_path(root, relative)
    if not path.is_file():
        raise ValueError(f"artifact missing: {relative}")
    try:
        expected_bytes = int(record.get("bytes", -1))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid artifact byte count: {relative}") from exc
    if path.stat().st_size != expected_bytes:
        raise ValueError(f"artifact byte count mismatch: {relative}")
    if _file_sha256(path) != record.get("sha256"):
        raise ValueError(f"artifact checksum mismatch: {relative}")
    return relative


def _verify_artifacts(root: Path, manifest: dict[str, object]) -> tuple[list[dict[str, object]], set[str]]:
    """Verify all artifact hashes and return records plus their paths."""
    records = manifest.get("artifacts")
    if not isinstance(records, list) or not records:
        raise ValueError("manifest artifacts missing")
    paths = {_verify_artifact_record(root, record) for record in records}
    if len(paths) != len(records):
        raise ValueError("duplicate artifact path in manifest")
    return records, paths


def _stream_map(
    manifest: dict[str, object], expected_streams: set[tuple[str, str]]
) -> dict[tuple[str, str], dict[str, object]]:
    """Build and validate the exact manifest stream map."""
    streams = manifest.get("streams")
    if not isinstance(streams, list):
        raise ValueError("manifest streams missing")
    valid_streams = [stream for stream in streams if isinstance(stream, dict)]
    if len(valid_streams) != len(streams):
        raise ValueError("manifest contains invalid stream record")
    mapping = {
        (str(stream.get("pair", "")), str(stream.get("timeframe", ""))): stream
        for stream in valid_streams
    }
    if len(mapping) != len(valid_streams):
        raise ValueError("duplicate stream record in manifest")
    if set(mapping) != expected_streams:
        raise ValueError("stream scope mismatch")
    return mapping


def _validate_stream_metadata(
    stream: dict[str, object],
    summary: dict[str, object],
    *,
    pair: str,
    timeframe: str,
) -> None:
    """Cross-check one stream's manifest statistics against its CSV."""
    if int(stream.get("rows", -1)) != summary["rows"]:
        raise ValueError(f"manifest row count mismatch for {pair} {timeframe}")
    if stream.get("first_time") != summary["first_time"]:
        raise ValueError(f"manifest first timestamp mismatch for {pair} {timeframe}")
    if stream.get("last_time") != summary["last_time"]:
        raise ValueError(f"manifest last timestamp mismatch for {pair} {timeframe}")


def _verify_stream(
    *,
    root: Path,
    pair: str,
    timeframe: str,
    stream: dict[str, object],
    artifact_paths: set[str],
    raw_start: datetime,
    raw_end: datetime,
    evaluation_start: datetime,
    min_warmup_bars: int,
) -> dict[str, object]:
    """Verify one expected stream and return its compact summary."""
    expected_csv = f"candles/{pair}_{timeframe}.csv"
    if str(stream.get("csv", "")) != expected_csv:
        raise ValueError(f"unexpected CSV path for {pair} {timeframe}")
    if expected_csv not in artifact_paths:
        raise ValueError(f"CSV missing from artifact manifest for {pair} {timeframe}")

    summary = verify_csv(
        _safe_artifact_path(root, expected_csv),
        raw_start=raw_start,
        raw_end=raw_end,
        evaluation_start=evaluation_start,
        min_warmup_bars=min_warmup_bars,
    )
    _validate_stream_metadata(stream, summary, pair=pair, timeframe=timeframe)
    return {
        "pair": pair,
        "timeframe": timeframe,
        **summary,
        "requests": stream.get("request_count"),
        "http_attempts": stream.get("http_attempts"),
        "provider_leading_overlaps_observed": stream.get("provider_leading_overlaps_observed", 0),
    }


def verify_dataset(
    *,
    dataset_root: Path,
    expected_dataset_id: str,
    raw_start: datetime,
    raw_end: datetime,
    evaluation_start: datetime,
    pairs: list[str],
    timeframes: list[str],
    min_warmup_bars: int,
) -> dict[str, object]:
    """Verify manifest, artifacts, candles, scope, and replay warm-up coverage."""
    root, manifest = _load_manifest(dataset_root, expected_dataset_id)
    requested_pairs, requested_tfs, expected_streams = _expected_scope(pairs, timeframes)
    _validate_manifest_scope_and_range(
        manifest,
        raw_start=raw_start,
        raw_end=raw_end,
        evaluation_start=evaluation_start,
        requested_pairs=requested_pairs,
        requested_tfs=requested_tfs,
        min_warmup_bars=min_warmup_bars,
    )
    artifact_records, artifact_paths = _verify_artifacts(root, manifest)
    streams = _stream_map(manifest, expected_streams)
    summaries = [
        _verify_stream(
            root=root,
            pair=pair,
            timeframe=timeframe,
            stream=streams[(pair, timeframe)],
            artifact_paths=artifact_paths,
            raw_start=raw_start,
            raw_end=raw_end,
            evaluation_start=evaluation_start,
            min_warmup_bars=min_warmup_bars,
        )
        for pair, timeframe in sorted(expected_streams)
    ]

    return {
        "status": "PASS",
        "dataset_id": expected_dataset_id,
        "dataset_root": str(root),
        "manifest_status": manifest.get("status"),
        "artifact_count": len(artifact_records),
        "artifact_hash_failures": 0,
        "stream_count": len(summaries),
        "min_warmup_bars": min_warmup_bars,
        "evaluation_start_utc": iso_z(evaluation_start),
        "raw_start_utc": iso_z(raw_start),
        "raw_end_utc": iso_z(raw_end),
        "streams": summaries,
    }


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description="Offline integrity verification for one BotA replay dataset.")
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--expected-dataset-id", required=True)
    parser.add_argument("--raw-start-utc", required=True)
    parser.add_argument("--raw-end-utc", required=True)
    parser.add_argument("--evaluation-start-utc", required=True)
    parser.add_argument("--pairs", nargs="+", default=["EURUSD", "GBPUSD"])
    parser.add_argument("--timeframes", nargs="+", default=["M15", "H1", "H4", "D1"])
    parser.add_argument("--min-warmup-bars", type=int, default=500)
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = _parser().parse_args(argv)
    try:
        result = verify_dataset(
            dataset_root=Path(args.dataset_root),
            expected_dataset_id=args.expected_dataset_id,
            raw_start=parse_utc(args.raw_start_utc),
            raw_end=parse_utc(args.raw_end_utc),
            evaluation_start=parse_utc(args.evaluation_start_utc),
            pairs=args.pairs,
            timeframes=args.timeframes,
            min_warmup_bars=args.min_warmup_bars,
        )
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
