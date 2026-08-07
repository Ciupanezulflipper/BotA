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
    text = str(value).strip()
    if not text:
        raise ValueError("timestamp is empty")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_pair(value: str) -> str:
    pair = str(value).replace("/", "").replace("_", "").replace(" ", "").upper()
    if pair not in ALLOWED_PAIRS:
        raise ValueError(f"unsupported pair: {value}")
    return pair


def normalize_tf(value: str) -> str:
    tf = str(value).strip().upper()
    if tf == "1D":
        tf = "D1"
    if tf not in ALLOWED_TIMEFRAMES:
        raise ValueError(f"unsupported timeframe: {value}")
    return tf


def _safe_artifact_path(dataset_root: Path, relative: str) -> Path:
    if not relative or Path(relative).is_absolute():
        raise ValueError(f"invalid artifact path: {relative}")
    root = dataset_root.resolve()
    path = (root / relative).resolve()
    if os.path.commonpath([str(root), str(path)]) != str(root):
        raise ValueError(f"artifact escapes dataset root: {relative}")
    return path


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _finite_positive(value: str, field: str, line_no: int) -> float:
    try:
        number = float(value)
    except Exception as exc:
        raise ValueError(f"line {line_no}: invalid {field}") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"line {line_no}: invalid {field}")
    return number


def verify_csv(
    path: Path,
    *,
    raw_start: datetime,
    raw_end: datetime,
    evaluation_start: datetime,
    min_warmup_bars: int,
) -> dict[str, object]:
    rows: list[datetime] = []

    with path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != CSV_HEADER:
            raise ValueError(f"unexpected CSV header in {path.name}")

        for line_no, row in enumerate(reader, start=2):
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
            rows.append(stamp)

    if not rows:
        raise ValueError("CSV contains no candles")
    if any(left >= right for left, right in zip(rows, rows[1:])):
        raise ValueError("timestamps are not strictly increasing")

    pre_evaluation = sum(stamp < evaluation_start for stamp in rows)
    evaluation_rows = sum(evaluation_start <= stamp < raw_end for stamp in rows)

    if pre_evaluation < min_warmup_bars:
        raise ValueError(
            f"insufficient warm-up candles: {pre_evaluation} < {min_warmup_bars}"
        )
    if evaluation_rows <= 0:
        raise ValueError("no candles in evaluation range")

    return {
        "rows": len(rows),
        "pre_evaluation_rows": pre_evaluation,
        "evaluation_rows": evaluation_rows,
        "first_time": iso_z(rows[0]),
        "last_time": iso_z(rows[-1]),
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
    root = dataset_root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"dataset root missing: {root}")
    if (root / "FAILED.json").exists():
        raise ValueError("FAILED.json exists; dataset is not replay-eligible")

    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("manifest.json missing")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "COMPLETE":
        raise ValueError("manifest status is not COMPLETE")
    if manifest.get("dataset_id") != expected_dataset_id:
        raise ValueError("dataset id mismatch")
    if manifest.get("provider") != "oanda" or manifest.get("price_component") != "M":
        raise ValueError("provider/price contract mismatch")
    if manifest.get("production_cache_touched") is not False:
        raise ValueError("manifest does not prove production cache isolation")

    requested_pairs = list(dict.fromkeys(normalize_pair(pair) for pair in pairs))
    requested_tfs = list(dict.fromkeys(normalize_tf(tf) for tf in timeframes))
    expected_streams = {(pair, tf) for pair in requested_pairs for tf in requested_tfs}

    if set(manifest.get("pairs", [])) != set(requested_pairs):
        raise ValueError("pair scope mismatch")
    if set(manifest.get("timeframes", [])) != set(requested_tfs):
        raise ValueError("timeframe scope mismatch")

    range_info = manifest.get("range") or {}
    if range_info.get("start_utc") != iso_z(raw_start):
        raise ValueError("raw start mismatch")
    if range_info.get("end_utc_exclusive") != iso_z(raw_end):
        raise ValueError("raw end mismatch")
    if not raw_start < evaluation_start < raw_end:
        raise ValueError("evaluation start must be inside raw range")
    if min_warmup_bars < 1:
        raise ValueError("min warm-up bars must be positive")

    artifact_records = manifest.get("artifacts")
    if not isinstance(artifact_records, list) or not artifact_records:
        raise ValueError("manifest artifacts missing")

    artifact_hash_failures = 0
    artifact_paths: set[str] = set()
    for record in artifact_records:
        if not isinstance(record, dict):
            artifact_hash_failures += 1
            continue
        relative = str(record.get("path", ""))
        try:
            path = _safe_artifact_path(root, relative)
        except ValueError:
            artifact_hash_failures += 1
            continue
        artifact_paths.add(relative)
        if not path.is_file():
            artifact_hash_failures += 1
            continue
        if path.stat().st_size != int(record.get("bytes", -1)):
            artifact_hash_failures += 1
            continue
        if _file_sha256(path) != record.get("sha256"):
            artifact_hash_failures += 1

    if artifact_hash_failures:
        raise ValueError(f"artifact checksum failures: {artifact_hash_failures}")

    streams = manifest.get("streams")
    if not isinstance(streams, list):
        raise ValueError("manifest streams missing")
    stream_map = {
        (stream.get("pair"), stream.get("timeframe")): stream
        for stream in streams
        if isinstance(stream, dict)
    }
    if set(stream_map) != expected_streams:
        raise ValueError("stream scope mismatch")

    stream_summaries: list[dict[str, object]] = []
    for pair, tf in sorted(expected_streams):
        stream = stream_map[(pair, tf)]
        relative_csv = str(stream.get("csv", ""))
        expected_csv = f"candles/{pair}_{tf}.csv"
        if relative_csv != expected_csv:
            raise ValueError(f"unexpected CSV path for {pair} {tf}")
        if expected_csv not in artifact_paths:
            raise ValueError(f"CSV missing from artifact manifest for {pair} {tf}")

        csv_path = _safe_artifact_path(root, expected_csv)
        summary = verify_csv(
            csv_path,
            raw_start=raw_start,
            raw_end=raw_end,
            evaluation_start=evaluation_start,
            min_warmup_bars=min_warmup_bars,
        )
        if int(stream.get("rows", -1)) != summary["rows"]:
            raise ValueError(f"manifest row count mismatch for {pair} {tf}")
        if stream.get("first_time") != summary["first_time"]:
            raise ValueError(f"manifest first timestamp mismatch for {pair} {tf}")
        if stream.get("last_time") != summary["last_time"]:
            raise ValueError(f"manifest last timestamp mismatch for {pair} {tf}")

        stream_summaries.append(
            {
                "pair": pair,
                "timeframe": tf,
                **summary,
                "requests": stream.get("request_count"),
                "http_attempts": stream.get("http_attempts"),
                "provider_leading_overlaps_observed": stream.get(
                    "provider_leading_overlaps_observed", 0
                ),
            }
        )

    return {
        "status": "PASS",
        "dataset_id": expected_dataset_id,
        "dataset_root": str(root),
        "manifest_status": manifest.get("status"),
        "artifact_count": len(artifact_records),
        "artifact_hash_failures": 0,
        "stream_count": len(stream_summaries),
        "min_warmup_bars": min_warmup_bars,
        "evaluation_start_utc": iso_z(evaluation_start),
        "raw_start_utc": iso_z(raw_start),
        "raw_end_utc": iso_z(raw_end),
        "streams": stream_summaries,
    }


def _parser() -> argparse.ArgumentParser:
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
