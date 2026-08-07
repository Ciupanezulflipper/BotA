#!/usr/bin/env python3
"""Acquire immutable historical OANDA midpoint candles for BotA replay.

This tool is deliberately separate from the production candle cache. It writes
only below data/replay/<dataset-id>, uses the same OANDA midpoint candle
contract as production (price=M), persists raw provider responses, and emits a
checksum manifest suitable for deterministic replay inputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import http.client
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import pairwise
from pathlib import Path
from typing import Callable, Iterable, Mapping
from urllib.parse import urlencode, urlsplit

ALLOWED_PAIRS = {"EURUSD", "GBPUSD"}
TF_TO_GRANULARITY = {"M15": "M15", "H1": "H1", "H4": "H4", "D1": "D"}
TF_SECONDS = {"M15": 15 * 60, "H1": 60 * 60, "H4": 4 * 60 * 60, "D1": 24 * 60 * 60}
ALLOWED_OANDA_HOSTS = {"api-fxpractice.oanda.com", "api-fxtrade.oanda.com"}
DEFAULT_OANDA_URL = "https://api-fxpractice.oanda.com"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
DATASET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
DOTENV_KEYS = {"OANDA_API_TOKEN", "OANDA_API_URL"}
MAX_HTTP_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 0.5


@dataclass(frozen=True)
class Candle:
    """One complete midpoint candle returned by OANDA."""

    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class HttpResponse:
    """Bounded HTTP response used by the acquisition layer."""

    status: int
    headers: dict[str, str]
    body: bytes


Transport = Callable[[str, str, str, float], HttpResponse]
SleepFn = Callable[[float], None]


def utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


def iso_z(value: datetime) -> str:
    """Render an aware datetime in UTC Z form."""
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    """Parse an ISO-8601 UTC/offset timestamp into UTC."""
    text = str(value).strip()
    if not text:
        raise ValueError("timestamp is empty")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


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
    if tf not in TF_TO_GRANULARITY:
        raise ValueError(f"unsupported timeframe: {value}")
    return tf


def instrument_for_pair(pair: str) -> str:
    """Map EURUSD form into the OANDA EUR_USD instrument form."""
    normalized = normalize_pair(pair)
    return f"{normalized[:3]}_{normalized[3:]}"


def safe_dotenv_values(repo_root: Path) -> dict[str, str]:
    """Read only OANDA keys from .env as data; never execute shell syntax."""
    path = repo_root / ".env"
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in DOTENV_KEYS:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def oanda_config(repo_root: Path, environ: Mapping[str, str] | None = None) -> tuple[str, str]:
    """Resolve production-compatible OANDA URL/token without printing secrets."""
    env = dict(os.environ if environ is None else environ)
    dotenv = safe_dotenv_values(repo_root)
    token = env.get("OANDA_API_TOKEN", "").strip() or dotenv.get("OANDA_API_TOKEN", "").strip()
    base_url = env.get("OANDA_API_URL", "").strip() or dotenv.get("OANDA_API_URL", "").strip() or DEFAULT_OANDA_URL
    validate_base_url(base_url)
    return base_url.rstrip("/"), token


def validate_base_url(base_url: str) -> str:
    """Require HTTPS and an exact approved OANDA API host."""
    parsed = urlsplit(str(base_url).strip())
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_OANDA_HOSTS:
        raise ValueError("OANDA_API_URL must use an approved OANDA HTTPS host")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("OANDA_API_URL must not contain credentials or a custom port")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("OANDA_API_URL must be a bare API origin")
    return parsed.hostname


def validate_dataset_id(dataset_id: str) -> str:
    """Validate a dataset id without touching the filesystem."""
    if not DATASET_ID_RE.fullmatch(dataset_id):
        raise ValueError("dataset-id must match [A-Za-z0-9][A-Za-z0-9._-]{0,63}")
    return dataset_id


def dataset_path_preview(repo_root: Path, dataset_id: str) -> Path:
    """Validate a dataset id/path without creating directories."""
    validate_dataset_id(dataset_id)
    return repo_root.resolve() / "data" / "replay" / dataset_id


def dataset_path(repo_root: Path, dataset_id: str) -> Path:
    """Return a contained immutable dataset path below data/replay."""
    validate_dataset_id(dataset_id)
    root = repo_root.resolve()
    replay_root = root / "data" / "replay"
    replay_root.mkdir(parents=True, exist_ok=True)
    if replay_root.is_symlink():
        raise ValueError("data/replay must not be a symlink")
    resolved_replay = replay_root.resolve()
    if os.path.commonpath([str(root), str(resolved_replay)]) != str(root):
        raise ValueError("data/replay escapes repository root")
    target = replay_root / dataset_id
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"immutable dataset already exists: {target}")
    if target.parent.resolve() != resolved_replay:
        raise ValueError("dataset path escapes data/replay")
    return target


def plan_windows(
    start_utc: datetime,
    end_utc: datetime,
    timeframe: str,
    max_candles_per_request: int = 4500,
) -> list[tuple[datetime, datetime]]:
    """Plan overlapping from/to windows below OANDA's 5000-candle cap."""
    tf = normalize_tf(timeframe)
    start = start_utc.astimezone(timezone.utc)
    end = end_utc.astimezone(timezone.utc)
    if end <= start:
        raise ValueError("end must be after start")
    if max_candles_per_request < 2 or max_candles_per_request > 5000:
        raise ValueError("max-candles-per-request must be in [2, 5000]")
    step = timedelta(seconds=TF_SECONDS[tf] * (max_candles_per_request - 1))
    windows: list[tuple[datetime, datetime]] = []
    cursor = start
    while cursor < end:
        request_end = min(cursor + step, end)
        windows.append((cursor, request_end))
        if request_end >= end:
            break
        cursor = request_end
    return windows


def request_path(pair: str, timeframe: str, start: datetime, end: datetime) -> str:
    """Build a production-faithful OANDA midpoint candle request path."""
    instrument = instrument_for_pair(pair)
    tf = normalize_tf(timeframe)
    params = {
        "granularity": TF_TO_GRANULARITY[tf],
        "price": "M",
        "from": iso_z(start),
        "to": iso_z(end),
        "includeFirst": "true",
    }
    return f"/v3/instruments/{instrument}/candles?{urlencode(params)}"


def https_transport(base_url: str, path_and_query: str, token: str, timeout_seconds: float) -> HttpResponse:
    """Execute one bounded GET to an allowlisted OANDA HTTPS origin."""
    host = validate_base_url(base_url)
    if not path_and_query.startswith("/v3/instruments/") or "Authorization" in path_and_query:
        raise ValueError("unexpected OANDA request path")
    if not token.strip():
        raise PermissionError("OANDA_API_TOKEN is missing")
    if timeout_seconds <= 0 or timeout_seconds > 120:
        raise ValueError("timeout must be in (0, 120]")
    connection = http.client.HTTPSConnection(host, 443, timeout=timeout_seconds)
    try:
        connection.request(
            "GET",
            path_and_query,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token.strip()}",
                "User-Agent": "BotA-Historical-Candles/1",
            },
        )
        response = connection.getresponse()
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise RuntimeError("OANDA response exceeded bounded size")
        headers = {str(k): str(v) for k, v in response.getheaders()}
        return HttpResponse(status=int(response.status), headers=headers, body=body)
    finally:
        connection.close()


def _finite_positive(value: object, field: str) -> float:
    number = float(str(value))
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"invalid {field}")
    return number


def parse_oanda_payload(body: bytes) -> list[Candle]:
    """Parse complete midpoint candles and validate OHLC structure."""
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid OANDA JSON response") from exc
    raw_candles = payload.get("candles")
    if not isinstance(raw_candles, list):
        raise ValueError("OANDA response missing candles array")
    candles: list[Candle] = []
    for raw in raw_candles:
        if not isinstance(raw, dict) or raw.get("complete") is not True:
            continue
        mid = raw.get("mid")
        if not isinstance(mid, dict):
            raise ValueError("complete OANDA candle missing midpoint prices")
        stamp = parse_utc(str(raw.get("time", "")))
        opened = _finite_positive(mid.get("o"), "open")
        high = _finite_positive(mid.get("h"), "high")
        low = _finite_positive(mid.get("l"), "low")
        close = _finite_positive(mid.get("c"), "close")
        if high < max(opened, close) or low > min(opened, close) or low > high:
            raise ValueError("invalid OANDA candle OHLC ordering")
        volume = int(raw.get("volume", 0))
        if volume < 0:
            raise ValueError("invalid OANDA candle volume")
        candles.append(Candle(stamp, opened, high, low, close, volume))
    return candles


def reconcile_candles(chunks: Iterable[Iterable[Candle]]) -> tuple[list[Candle], int]:
    """Sort chunks, deduplicate identical boundaries, and reject conflicts."""
    by_time: dict[datetime, Candle] = {}
    duplicates = 0
    for chunk in chunks:
        for candle in chunk:
            existing = by_time.get(candle.time)
            if existing is None:
                by_time[candle.time] = candle
            elif existing == candle:
                duplicates += 1
            else:
                raise ValueError(f"conflicting duplicate candle at {iso_z(candle.time)}")
    return [by_time[key] for key in sorted(by_time)], duplicates


def write_once(path: Path, data: bytes) -> None:
    """Create one artifact without overwrite."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def atomic_json_once(path: Path, payload: object) -> None:
    """Persist canonical JSON exactly once."""
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
    write_once(path, data)


def response_metadata(response: HttpResponse) -> dict[str, object]:
    """Return bounded non-secret response metadata."""
    wanted = {"date", "requestid", "content-type", "content-length"}
    selected = {k: v for k, v in response.headers.items() if k.lower() in wanted}
    return {"status": response.status, "headers": selected, "body_bytes": len(response.body)}


def write_csv(path: Path, candles: list[Candle]) -> None:
    """Write replay candles in the production five-column CSV shape."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["time", "open", "high", "low", "close"])
        for candle in candles:
            writer.writerow(
                [
                    candle.time.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    f"{candle.open:.8f}",
                    f"{candle.high:.8f}",
                    f"{candle.low:.8f}",
                    f"{candle.close:.8f}",
                ]
            )
        handle.flush()
        os.fsync(handle.fileno())


def gap_stats(candles: list[Candle], timeframe: str) -> tuple[int, int]:
    """Count spacing gaps without treating normal market closures as corruption."""
    expected = TF_SECONDS[normalize_tf(timeframe)]
    gaps: list[int] = []
    for left, right in pairwise(candles):
        delta = int((right.time - left.time).total_seconds())
        if delta > expected:
            gaps.append(delta)
    return len(gaps), max(gaps, default=0)


def file_record(dataset_root: Path, path: Path) -> dict[str, object]:
    """Return checksum metadata for one immutable artifact."""
    data = path.read_bytes()
    return {
        "path": path.relative_to(dataset_root).as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _retryable_status(status: int) -> bool:
    """Return whether a bounded retry is appropriate for this HTTP status."""
    return status == 429 or 500 <= status <= 599


def _fetch_chunk_with_retries(
    *,
    dataset_root: Path,
    pair: str,
    timeframe: str,
    chunk_index: int,
    path_and_query: str,
    base_url: str,
    token: str,
    timeout_seconds: float,
    transport: Transport,
    sleep_fn: SleepFn,
) -> tuple[list[Candle], int]:
    """Fetch one chunk with bounded retry/backoff while preserving every response."""
    for attempt in range(1, MAX_HTTP_ATTEMPTS + 1):
        response = transport(base_url, path_and_query, token, timeout_seconds)
        stem = f"chunk-{chunk_index:04d}-attempt-{attempt:02d}"
        raw_path = dataset_root / "raw" / pair / timeframe / f"{stem}.json"
        metadata_path = dataset_root / "metadata" / pair / timeframe / f"{stem}.json"
        write_once(raw_path, response.body)
        atomic_json_once(
            metadata_path,
            {
                "request": {
                    "method": "GET",
                    "path_and_query": path_and_query,
                    "authorization_redacted": True,
                    "attempt": attempt,
                },
                "response": response_metadata(response),
            },
        )

        if 200 <= response.status < 300:
            return parse_oanda_payload(response.body), attempt

        if not _retryable_status(response.status) or attempt == MAX_HTTP_ATTEMPTS:
            raise RuntimeError(
                f"OANDA HTTP {response.status} for {pair} {timeframe} "
                f"chunk {chunk_index} attempt {attempt}"
            )

        sleep_fn(RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1)))

    raise RuntimeError(f"no successful response for {pair} {timeframe} chunk {chunk_index}")


def _validate_chunk_window(
    candles: list[Candle],
    *,
    pair: str,
    timeframe: str,
    window_start: datetime,
    window_end: datetime,
) -> int:
    """Validate provider-aligned candle starts around one explicit request window.

    OANDA may return one complete candle whose start precedes ``from`` when the
    requested timestamp falls inside an H4/D1 provider-aligned candle. That
    candle is valid evidence and can overlap the requested start, but it must
    be no older than one timeframe and there must never be more than one such
    leading candle. Candles after ``to`` remain fail-closed errors.
    """
    tf = normalize_tf(timeframe)
    duration = timedelta(seconds=TF_SECONDS[tf])
    leading = [candle for candle in candles if candle.time < window_start]
    trailing = [candle for candle in candles if candle.time > window_end]

    if trailing:
        raise ValueError(
            f"OANDA returned candle outside requested chunk for {pair} {tf}: "
            f"{iso_z(trailing[0].time)}"
        )

    invalid_leading = [
        candle
        for candle in leading
        if candle.time + duration <= window_start
    ]
    if len(leading) > 1 or invalid_leading:
        offending = invalid_leading[0] if invalid_leading else leading[0]
        raise ValueError(
            f"OANDA returned candle outside requested chunk for {pair} {tf}: "
            f"{iso_z(offending.time)}"
        )

    return len(leading)


def acquire_stream(
    *,
    dataset_root: Path,
    pair: str,
    timeframe: str,
    start_utc: datetime,
    end_utc: datetime,
    base_url: str,
    token: str,
    timeout_seconds: float,
    max_candles_per_request: int,
    transport: Transport = https_transport,
    sleep_fn: SleepFn = time.sleep,
) -> dict[str, object]:
    """Acquire and persist one pair/timeframe stream."""
    normalized_pair = normalize_pair(pair)
    tf = normalize_tf(timeframe)
    windows = plan_windows(start_utc, end_utc, tf, max_candles_per_request)
    parsed_chunks: list[list[Candle]] = []
    http_attempts = 0
    provider_leading_overlaps = 0

    for index, (window_start, window_end) in enumerate(windows):
        path_and_query = request_path(normalized_pair, tf, window_start, window_end)
        parsed, attempts = _fetch_chunk_with_retries(
            dataset_root=dataset_root,
            pair=normalized_pair,
            timeframe=tf,
            chunk_index=index,
            path_and_query=path_and_query,
            base_url=base_url,
            token=token,
            timeout_seconds=timeout_seconds,
            transport=transport,
            sleep_fn=sleep_fn,
        )
        http_attempts += attempts
        provider_leading_overlaps += _validate_chunk_window(
            parsed,
            pair=normalized_pair,
            timeframe=tf,
            window_start=window_start,
            window_end=window_end,
        )
        parsed_chunks.append(parsed)

    reconciled, duplicate_count = reconcile_candles(parsed_chunks)
    filtered = [c for c in reconciled if start_utc <= c.time < end_utc]
    if not filtered:
        raise ValueError(f"no complete candles returned for {normalized_pair} {tf}")
    if any(left.time >= right.time for left, right in pairwise(filtered)):
        raise ValueError("candle timestamps are not strictly increasing")

    csv_path = dataset_root / "candles" / f"{normalized_pair}_{tf}.csv"
    write_csv(csv_path, filtered)
    gaps, max_gap = gap_stats(filtered, tf)
    return {
        "pair": normalized_pair,
        "timeframe": tf,
        "provider_granularity": TF_TO_GRANULARITY[tf],
        "request_count": len(windows),
        "http_attempts": http_attempts,
        "rows": len(filtered),
        "first_time": iso_z(filtered[0].time),
        "last_time": iso_z(filtered[-1].time),
        "boundary_duplicates_removed": duplicate_count,
        "provider_leading_overlaps_observed": provider_leading_overlaps,
        "spacing_gaps": gaps,
        "max_gap_seconds": max_gap,
        "csv": csv_path.relative_to(dataset_root).as_posix(),
    }


def build_preview(
    *,
    repo_root: Path,
    dataset_id: str,
    pairs: list[str],
    timeframes: list[str],
    start_utc: datetime,
    end_utc: datetime,
    max_candles_per_request: int,
    base_url: str,
) -> dict[str, object]:
    """Build a no-network acquisition preview."""
    target = dataset_path_preview(repo_root, dataset_id)
    streams = []
    for pair in pairs:
        for timeframe in timeframes:
            windows = plan_windows(start_utc, end_utc, timeframe, max_candles_per_request)
            streams.append(
                {
                    "pair": normalize_pair(pair),
                    "timeframe": normalize_tf(timeframe),
                    "requests": len(windows),
                }
            )
    return {
        "mode": "preview",
        "network_permitted": False,
        "production_cache_touched": False,
        "dataset_root": str(target),
        "base_url": base_url,
        "range_start_utc": iso_z(start_utc),
        "range_end_utc": iso_z(end_utc),
        "streams": streams,
    }


def _normalize_scope(pairs: list[str], timeframes: list[str]) -> tuple[list[str], list[str]]:
    """Normalize pair/timeframe scope and require both dimensions."""
    normalized_pairs = list(dict.fromkeys(normalize_pair(pair) for pair in pairs))
    normalized_tfs = list(dict.fromkeys(normalize_tf(tf) for tf in timeframes))
    if not normalized_pairs or not normalized_tfs:
        raise ValueError("at least one pair and timeframe are required")
    return normalized_pairs, normalized_tfs


def _acquire_all_streams(
    *,
    target: Path,
    pairs: list[str],
    timeframes: list[str],
    start_utc: datetime,
    end_utc: datetime,
    base_url: str,
    token: str,
    timeout_seconds: float,
    max_candles_per_request: int,
    transport: Transport,
    sleep_fn: SleepFn,
) -> list[dict[str, object]]:
    """Acquire every requested pair/timeframe stream into one dataset root."""
    streams: list[dict[str, object]] = []
    for pair in pairs:
        for timeframe in timeframes:
            streams.append(
                acquire_stream(
                    dataset_root=target,
                    pair=pair,
                    timeframe=timeframe,
                    start_utc=start_utc,
                    end_utc=end_utc,
                    base_url=base_url,
                    token=token,
                    timeout_seconds=timeout_seconds,
                    max_candles_per_request=max_candles_per_request,
                    transport=transport,
                    sleep_fn=sleep_fn,
                )
            )
    return streams


def _dataset_artifacts(target: Path) -> list[dict[str, object]]:
    """Checksum all persisted data artifacts except terminal status documents."""
    return [
        file_record(target, path)
        for path in sorted(target.rglob("*"))
        if path.is_file() and path.name not in {"manifest.json", "FAILED.json"}
    ]


def _write_failure_marker(target: Path, dataset_id: str, exc: Exception, recorded_at: datetime | None) -> None:
    """Best-effort immutable failure marker without masking the original error."""
    failure = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "status": "FAILED",
        "recorded_at_utc": iso_z(recorded_at or utc_now()),
        "error_type": type(exc).__name__,
        "error": str(exc)[:500],
        "production_cache_touched": False,
    }
    try:
        atomic_json_once(target / "FAILED.json", failure)
    except OSError as write_error:
        print(
            json.dumps(
                {"status": "FAILURE_RECORD_UNWRITTEN", "error": str(write_error)[:200]},
                sort_keys=True,
            ),
            file=sys.stderr,
        )


def acquire_dataset(
    *,
    repo_root: Path,
    dataset_id: str,
    pairs: list[str],
    timeframes: list[str],
    start_utc: datetime,
    end_utc: datetime,
    base_url: str,
    token: str,
    timeout_seconds: float = 30.0,
    max_candles_per_request: int = 4500,
    transport: Transport = https_transport,
    sleep_fn: SleepFn = time.sleep,
    recorded_at: datetime | None = None,
) -> dict[str, object]:
    """Acquire a complete immutable replay dataset and checksum manifest."""
    if not token.strip():
        raise PermissionError("OANDA_API_TOKEN is missing")
    validate_base_url(base_url)
    normalized_pairs, normalized_tfs = _normalize_scope(pairs, timeframes)
    start = start_utc.astimezone(timezone.utc)
    end = end_utc.astimezone(timezone.utc)
    if end <= start:
        raise ValueError("end must be after start")

    target = dataset_path(repo_root, dataset_id)
    target.mkdir(parents=False, exist_ok=False)
    try:
        streams = _acquire_all_streams(
            target=target,
            pairs=normalized_pairs,
            timeframes=normalized_tfs,
            start_utc=start,
            end_utc=end,
            base_url=base_url,
            token=token,
            timeout_seconds=timeout_seconds,
            max_candles_per_request=max_candles_per_request,
            transport=transport,
            sleep_fn=sleep_fn,
        )
        manifest = {
            "schema_version": 1,
            "dataset_id": dataset_id,
            "status": "COMPLETE",
            "recorded_at_utc": iso_z(recorded_at or utc_now()),
            "provider": "oanda",
            "price_component": "M",
            "base_url": base_url,
            "range": {"start_utc": iso_z(start), "end_utc_exclusive": iso_z(end)},
            "pairs": normalized_pairs,
            "timeframes": normalized_tfs,
            "production_cache_touched": False,
            "streams": streams,
            "artifacts": _dataset_artifacts(target),
        }
        atomic_json_once(target / "manifest.json", manifest)
        return manifest
    except Exception as exc:
        _write_failure_marker(target, dataset_id, exc, recorded_at)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Immutable historical OANDA candle acquisition for BotA replay.")
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--start-utc", required=True)
    parser.add_argument("--end-utc", required=True)
    parser.add_argument("--pairs", nargs="+", default=["EURUSD", "GBPUSD"])
    parser.add_argument("--timeframes", nargs="+", default=["M15", "H1", "H4", "D1"])
    parser.add_argument("--max-candles-per-request", type=int, default=4500)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--execute", action="store_true", help="Permit read-only OANDA network acquisition.")
    parser.add_argument("--repo-root", default=None, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; preview is the default and never performs network I/O."""
    args = _parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[1]
    try:
        start = parse_utc(args.start_utc)
        end = parse_utc(args.end_utc)
        base_url, token = oanda_config(repo_root)
        if not args.execute:
            preview = build_preview(
                repo_root=repo_root,
                dataset_id=args.dataset_id,
                pairs=args.pairs,
                timeframes=args.timeframes,
                start_utc=start,
                end_utc=end,
                max_candles_per_request=args.max_candles_per_request,
                base_url=base_url,
            )
            print(json.dumps(preview, sort_keys=True, indent=2))
            return 0
        manifest = acquire_dataset(
            repo_root=repo_root,
            dataset_id=args.dataset_id,
            pairs=args.pairs,
            timeframes=args.timeframes,
            start_utc=start,
            end_utc=end,
            base_url=base_url,
            token=token,
            timeout_seconds=args.timeout_seconds,
            max_candles_per_request=args.max_candles_per_request,
        )
        print(
            json.dumps(
                {
                    "status": manifest["status"],
                    "dataset_id": manifest["dataset_id"],
                    "dataset_root": str(repo_root / "data" / "replay" / args.dataset_id),
                    "streams": [
                        {
                            "pair": stream["pair"],
                            "timeframe": stream["timeframe"],
                            "rows": stream["rows"],
                            "requests": stream["request_count"],
                            "http_attempts": stream["http_attempts"],
                        }
                        for stream in manifest["streams"]
                    ],
                },
                sort_keys=True,
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        print(
            json.dumps({"status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)[:500]}, sort_keys=True),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
