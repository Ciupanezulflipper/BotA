from __future__ import annotations

import argparse
import csv
import hashlib
import http.client
import io
import json
import math
import os
import ssl
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable, Mapping
from urllib.parse import urlencode

TOKEN_ENV = "BOTA_AUDIT_OANDA_TOKEN"
EXECUTION_PHRASE = "I_AUTHORIZE_READ_ONLY_OANDA_ACQUISITION"
ALLOWED_HOSTS = {"api-fxpractice.oanda.com", "api-fxtrade.oanda.com"}
DEFAULT_HOST = "api-fxpractice.oanda.com"
DEFAULT_INSTRUMENTS = ("EUR_USD", "GBP_USD")
DEFAULT_GRANULARITIES = ("M15", "H1", "H4", "D")
GRANULARITY_SECONDS = {"M15": 900, "H1": 3600, "H4": 14400, "D": 86400}
MAX_CANDLES_PER_REQUEST = 5000
ERR_UNAPPROVED_HOST = "unapproved OANDA host"


@dataclass(frozen=True)
class PlannedRequest:
    instrument: str
    granularity: str
    start_utc: str
    end_utc: str
    path_and_query: str


@dataclass(frozen=True)
class TransportResponse:
    status: int
    headers: dict[str, str]
    body: bytes


Transport = Callable[[str, str, Mapping[str, str], float], TransportResponse]


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def validate_output_root(output_root: Path, repository_root: Path | None = None) -> Path:
    root = output_root.expanduser().resolve()
    if root == Path(root.anchor):
        raise ValueError("output root must not be filesystem root")
    if repository_root is not None and _is_within(root, repository_root):
        raise ValueError("historical artifacts must be written outside the BotA repository")
    return root


def write_once(root: Path, relative_path: str, payload: bytes) -> Path:
    destination = (root / relative_path).resolve()
    if not _is_within(destination, root):
        raise ValueError("artifact path escapes output root")
    if destination.exists():
        raise FileExistsError(f"write-once artifact already exists: {relative_path}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination


def _validated_scope(
    instruments: Iterable[str],
    granularities: Iterable[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    instrument_tuple = tuple(instruments)
    granularity_tuple = tuple(granularities)
    bad_instrument = next((x for x in instrument_tuple if x not in DEFAULT_INSTRUMENTS), None)
    if bad_instrument:
        raise ValueError(f"unsupported audit instrument: {bad_instrument}")
    bad_granularity = next((x for x in granularity_tuple if x not in GRANULARITY_SECONDS), None)
    if bad_granularity:
        raise ValueError(f"unsupported audit granularity: {bad_granularity}")
    return instrument_tuple, granularity_tuple


def _validated_boundaries(
    start_utc: datetime,
    end_utc: datetime,
    max_candles: int,
) -> tuple[datetime, datetime]:
    if start_utc.tzinfo is None or end_utc.tzinfo is None:
        raise ValueError("plan boundaries must be timezone-aware")
    start = start_utc.astimezone(timezone.utc)
    end = end_utc.astimezone(timezone.utc)
    if end <= start:
        raise ValueError("end_utc must be after start_utc")
    if not 2 <= max_candles <= MAX_CANDLES_PER_REQUEST:
        raise ValueError(f"max_candles must be within [2, {MAX_CANDLES_PER_REQUEST}]")
    return start, end


def _request_path(
    instrument: str,
    granularity: str,
    start_utc: datetime,
    end_utc: datetime,
) -> str:
    query = urlencode(
        {
            "from": _z(start_utc),
            "to": _z(end_utc),
            "granularity": granularity,
            "price": "M",
            "includeFirst": "true",
        }
    )
    path = f"/v3/instruments/{instrument}/candles?{query}"
    if "count=" in path:
        raise AssertionError("explicit from/to acquisition must not use count")
    return path


def _series_requests(
    instrument: str,
    granularity: str,
    start_utc: datetime,
    end_utc: datetime,
    max_candles: int,
) -> list[PlannedRequest]:
    span = timedelta(seconds=GRANULARITY_SECONDS[granularity] * (max_candles - 1))
    rows: list[PlannedRequest] = []
    cursor = start_utc
    while cursor < end_utc:
        chunk_end = min(end_utc, cursor + span)
        rows.append(
            PlannedRequest(
                instrument=instrument,
                granularity=granularity,
                start_utc=_z(cursor),
                end_utc=_z(chunk_end),
                path_and_query=_request_path(instrument, granularity, cursor, chunk_end),
            )
        )
        cursor = chunk_end
    return rows


def plan_requests(
    *,
    start_utc: datetime,
    end_utc: datetime,
    instruments: Iterable[str] = DEFAULT_INSTRUMENTS,
    granularities: Iterable[str] = DEFAULT_GRANULARITIES,
    max_candles: int = MAX_CANDLES_PER_REQUEST,
) -> list[PlannedRequest]:
    start, end = _validated_boundaries(start_utc, end_utc, max_candles)
    instrument_tuple, granularity_tuple = _validated_scope(instruments, granularities)
    return [
        request
        for instrument in instrument_tuple
        for granularity in granularity_tuple
        for request in _series_requests(instrument, granularity, start, end, max_candles)
    ]


def build_preview(
    *,
    start_utc: datetime,
    end_utc: datetime,
    output_root: Path,
    run_id: str,
    instruments: Iterable[str] = DEFAULT_INSTRUMENTS,
    granularities: Iterable[str] = DEFAULT_GRANULARITIES,
    max_candles: int = MAX_CANDLES_PER_REQUEST,
    host: str = DEFAULT_HOST,
) -> dict:
    if host not in ALLOWED_HOSTS:
        raise ValueError(ERR_UNAPPROVED_HOST)
    instrument_tuple, granularity_tuple = _validated_scope(instruments, granularities)
    planned = plan_requests(
        start_utc=start_utc,
        end_utc=end_utc,
        instruments=instrument_tuple,
        granularities=granularity_tuple,
        max_candles=max_candles,
    )
    serial = [asdict(item) for item in planned]
    plan_bytes = json.dumps(serial, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "status": "PREVIEW",
        "mode": "dry_run_no_network",
        "network_permitted": False,
        "run_id": run_id,
        "output_root": str(output_root.expanduser()),
        "host": host,
        "token_environment_variable": TOKEN_ENV,
        "authorization_phrase_required": EXECUTION_PHRASE,
        "instruments": list(instrument_tuple),
        "granularities": list(granularity_tuple),
        "request_count": len(serial),
        "plan_sha256": _sha256_bytes(plan_bytes),
        "requests": serial,
    }


def _tls_context() -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_default_certs()
    return context


def _default_transport(
    host: str,
    path_and_query: str,
    headers: Mapping[str, str],
    timeout_seconds: float,
) -> TransportResponse:
    if host not in ALLOWED_HOSTS:
        raise ValueError(ERR_UNAPPROVED_HOST)
    if not path_and_query.startswith("/v3/instruments/"):
        raise ValueError("unexpected OANDA request path")
    connection = http.client.HTTPSConnection(
        host,
        timeout=timeout_seconds,
        context=_tls_context(),
    )
    try:
        connection.request("GET", path_and_query, headers=dict(headers))
        response = connection.getresponse()
        return TransportResponse(
            status=int(response.status),
            headers={str(key): str(value) for key, value in response.getheaders()},
            body=response.read(),
        )
    finally:
        connection.close()


def _redacted_request_metadata(host: str, request: PlannedRequest) -> bytes:
    doc = {
        "method": "GET",
        "scheme": "https",
        "host": host,
        "path_and_query": request.path_and_query,
        "authorization_header_persisted": False,
        "instrument": request.instrument,
        "granularity": request.granularity,
        "start_utc": request.start_utc,
        "end_utc": request.end_utc,
    }
    return (json.dumps(doc, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _response_metadata(response: TransportResponse) -> bytes:
    allowed = {"content-type", "date", "requestid", "request-id"}
    headers = {key: value for key, value in response.headers.items() if key.lower() in allowed}
    doc = {"status": response.status, "headers": headers}
    return (json.dumps(doc, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _finite_price(value: object) -> float:
    if not isinstance(value, (str, int, float)):
        raise ValueError("invalid candle price")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError("invalid candle price")
    return number


def _candle_row(raw: dict) -> dict | None:
    if raw.get("complete") is not True:
        return None
    mid = raw.get("mid")
    if not isinstance(mid, dict):
        raise ValueError("complete candle missing midpoint prices")
    opened = _finite_price(mid.get("o"))
    high = _finite_price(mid.get("h"))
    low = _finite_price(mid.get("l"))
    close = _finite_price(mid.get("c"))
    if high < max(opened, close, low) or low > min(opened, close, high):
        raise ValueError("invalid OHLC ordering")
    volume = int(raw.get("volume", 0))
    if volume < 0:
        raise ValueError("invalid candle volume")
    return {
        "time": _z(_utc(str(raw.get("time", "")))),
        "open": opened,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "complete": True,
    }


def parse_oanda_candles(body: bytes) -> list[dict]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("OANDA response is not valid UTF-8 JSON") from exc
    raw_candles = payload.get("candles")
    if not isinstance(raw_candles, list):
        raise ValueError("OANDA response missing candles list")
    if any(not isinstance(raw, dict) for raw in raw_candles):
        raise ValueError("invalid candle object")
    return [row for raw in raw_candles if (row := _candle_row(raw)) is not None]


def reconcile_candles(chunks: Iterable[list[dict]]) -> list[dict]:
    by_time: dict[str, dict] = {}
    for row in (row for chunk in chunks for row in chunk):
        prior = by_time.get(row["time"])
        if prior is not None and prior != row:
            raise ValueError(f'conflicting duplicate candle timestamp: {row["time"]}')
        by_time[row["time"]] = row
    return [by_time[key] for key in sorted(by_time)]


def _canonical_csv(rows: list[dict]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["time", "open", "high", "low", "close", "volume", "complete"])
    writer.writerows(
        [
            row["time"],
            f'{row["open"]:.8f}',
            f'{row["high"]:.8f}',
            f'{row["low"]:.8f}',
            f'{row["close"]:.8f}',
            row["volume"],
            "true",
        ]
        for row in rows
    )
    return output.getvalue().encode("utf-8")


def _artifact_record(root: Path, path: Path) -> dict:
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": _sha256_file(path),
    }


def _validate_execution(
    token: str,
    authorization_phrase: str,
    host: str,
    timeout_seconds: float,
) -> None:
    if authorization_phrase != EXECUTION_PHRASE:
        raise PermissionError("explicit authorization phrase missing or incorrect")
    if not token.strip():
        raise PermissionError(f"missing ephemeral token environment variable: {TOKEN_ENV}")
    if host not in ALLOWED_HOSTS:
        raise ValueError(ERR_UNAPPROVED_HOST)
    if not 0 < timeout_seconds <= 120:
        raise ValueError("timeout_seconds must be within (0, 120]")


def _prepare_root(output_root: Path, repository_root: Path | None) -> Path:
    root = validate_output_root(output_root, repository_root)
    if root.exists() and any(root.iterdir()):
        raise FileExistsError("output root must be new or empty for immutable acquisition")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _persist_response(
    root: Path,
    request_id: str,
    host: str,
    request: PlannedRequest,
    response: TransportResponse,
) -> list[Path]:
    return [
        write_once(root, f"raw/{request_id}.json", response.body),
        write_once(
            root,
            f"metadata/{request_id}.request.json",
            _redacted_request_metadata(host, request),
        ),
        write_once(
            root,
            f"metadata/{request_id}.response.json",
            _response_metadata(response),
        ),
    ]


def _fetch_all(
    *,
    root: Path,
    planned: list[PlannedRequest],
    token: str,
    host: str,
    timeout_seconds: float,
    transport: Transport,
) -> tuple[dict[tuple[str, str], list[list[dict]]], list[dict], list[Path]]:
    grouped: dict[tuple[str, str], list[list[dict]]] = {}
    records: list[dict] = []
    artifacts: list[Path] = []
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token.strip()}",
        "User-Agent": "BotA-Historical-Acquisition/2026-08-07",
    }
    for index, request in enumerate(planned):
        response = transport(host, request.path_and_query, headers, timeout_seconds)
        request_id = f"request-{index:04d}"
        artifacts.extend(_persist_response(root, request_id, host, request, response))
        if not 200 <= response.status < 300:
            raise RuntimeError(f"OANDA HTTP status {response.status} for {request_id}")
        parsed = parse_oanda_candles(response.body)
        grouped.setdefault((request.instrument, request.granularity), []).append(parsed)
        records.append(
            {
                "request_id": request_id,
                "instrument": request.instrument,
                "granularity": request.granularity,
                "start_utc": request.start_utc,
                "end_utc": request.end_utc,
                "returned_complete_candles": len(parsed),
                "http_status": response.status,
            }
        )
    return grouped, records, artifacts


def _write_series(
    root: Path,
    grouped: dict[tuple[str, str], list[list[dict]]],
    instruments: tuple[str, ...],
    granularities: tuple[str, ...],
) -> tuple[list[dict], list[Path]]:
    records: list[dict] = []
    artifacts: list[Path] = []
    for instrument in instruments:
        for granularity in granularities:
            rows = reconcile_candles(grouped.get((instrument, granularity), []))
            if not rows:
                raise ValueError(f"no complete candles returned for {instrument} {granularity}")
            relative = f"canonical/{instrument}_{granularity}.csv"
            path = write_once(root, relative, _canonical_csv(rows))
            artifacts.append(path)
            records.append(
                {
                    "instrument": instrument,
                    "granularity": granularity,
                    "rows": len(rows),
                    "first_utc": rows[0]["time"],
                    "last_utc": rows[-1]["time"],
                    "canonical_path": relative,
                }
            )
    return records, artifacts


def _write_manifest(
    *,
    root: Path,
    run_id: str,
    start_utc: datetime,
    end_utc: datetime,
    host: str,
    planned: list[PlannedRequest],
    requests: list[dict],
    series: list[dict],
    artifacts: list[Path],
) -> Path:
    manifest = {
        "schema_version": 1,
        "purpose": "BotA immutable historical candle acquisition",
        "provider": "OANDA",
        "price_component": "midpoint",
        "complete_candles_only": True,
        "run_id": run_id,
        "range_start_utc": _z(start_utc),
        "range_end_utc_exclusive": _z(end_utc),
        "host": host,
        "token_persisted": False,
        "request_count": len(planned),
        "requests": requests,
        "series": series,
        "artifacts": sorted(
            (_artifact_record(root, path) for path in artifacts),
            key=lambda item: item["path"],
        ),
    }
    payload = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    return write_once(root, "manifest.json", payload)


def execute_acquisition(
    *,
    output_root: Path,
    run_id: str,
    start_utc: datetime,
    end_utc: datetime,
    token: str,
    authorization_phrase: str,
    repository_root: Path | None = None,
    instruments: Iterable[str] = DEFAULT_INSTRUMENTS,
    granularities: Iterable[str] = DEFAULT_GRANULARITIES,
    max_candles: int = MAX_CANDLES_PER_REQUEST,
    host: str = DEFAULT_HOST,
    timeout_seconds: float = 30.0,
    transport: Transport | None = None,
) -> dict:
    _validate_execution(token, authorization_phrase, host, timeout_seconds)
    instrument_tuple, granularity_tuple = _validated_scope(instruments, granularities)
    root = _prepare_root(output_root, repository_root)
    planned = plan_requests(
        start_utc=start_utc,
        end_utc=end_utc,
        instruments=instrument_tuple,
        granularities=granularity_tuple,
        max_candles=max_candles,
    )
    plan_payload = (
        json.dumps([asdict(item) for item in planned], sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    artifacts = [write_once(root, "plan/requests.json", plan_payload)]
    grouped, request_records, fetched_artifacts = _fetch_all(
        root=root,
        planned=planned,
        token=token,
        host=host,
        timeout_seconds=timeout_seconds,
        transport=transport or _default_transport,
    )
    artifacts.extend(fetched_artifacts)
    series, series_artifacts = _write_series(
        root,
        grouped,
        instrument_tuple,
        granularity_tuple,
    )
    artifacts.extend(series_artifacts)
    manifest_path = _write_manifest(
        root=root,
        run_id=run_id,
        start_utc=start_utc,
        end_utc=end_utc,
        host=host,
        planned=planned,
        requests=request_records,
        series=series,
        artifacts=artifacts,
    )
    return {
        "status": "PASS",
        "mode": "live_read_only",
        "run_id": run_id,
        "output_root": str(root),
        "request_count": len(planned),
        "series_count": len(series),
        "manifest_path": str(manifest_path),
        "manifest_sha256": _sha256_file(manifest_path),
        "token_persisted": False,
    }


def _verify_artifact(root: Path, artifact: dict) -> list[str]:
    relative = artifact.get("path")
    if not isinstance(relative, str):
        return ["invalid_artifact_path"]
    path = (root / relative).resolve()
    if not _is_within(path, root):
        return [f"path_escape:{relative}"]
    if not path.is_file():
        return [f"missing:{relative}"]
    failures = []
    if path.stat().st_size != int(artifact.get("bytes", -1)):
        failures.append(f"size:{relative}")
    if _sha256_file(path) != artifact.get("sha256"):
        failures.append(f"sha256:{relative}")
    return failures


def verify_manifest(output_root: Path) -> dict:
    root = output_root.expanduser().resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("manifest.json missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = [
        failure
        for artifact in manifest.get("artifacts", [])
        for failure in _verify_artifact(root, artifact)
    ]
    return {
        "status": "PASS" if not failures else "FAIL",
        "artifact_count": len(manifest.get("artifacts", [])),
        "failures": failures,
        "manifest_sha256": _sha256_file(manifest_path),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Immutable read-only OANDA historical candle acquisition for BotA forensics."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--output-root", required=True)
    common.add_argument("--run-id", default="bota-20260601-20260711")
    common.add_argument("--start-utc", default="2026-06-01T00:00:00Z")
    common.add_argument("--end-utc", default="2026-07-11T00:00:00Z")
    common.add_argument("--host", default=DEFAULT_HOST)
    common.add_argument("--max-candles", type=int, default=MAX_CANDLES_PER_REQUEST)
    subparsers.add_parser("preview", parents=[common])
    acquire = subparsers.add_parser("acquire", parents=[common])
    acquire.add_argument("--execute", action="store_true")
    acquire.add_argument("--authorization-phrase", default="")
    acquire.add_argument("--timeout-seconds", type=float, default=30.0)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--output-root", required=True)
    return parser


def _run_command(args: argparse.Namespace) -> dict:
    if args.command == "verify":
        return verify_manifest(Path(args.output_root))
    if args.command == "preview":
        return build_preview(
            start_utc=_utc(args.start_utc),
            end_utc=_utc(args.end_utc),
            output_root=Path(args.output_root),
            run_id=args.run_id,
            max_candles=args.max_candles,
            host=args.host,
        )
    if args.execute is not True:
        raise PermissionError("acquire requires --execute")
    return execute_acquisition(
        output_root=Path(args.output_root),
        run_id=args.run_id,
        start_utc=_utc(args.start_utc),
        end_utc=_utc(args.end_utc),
        token=os.environ.get(TOKEN_ENV, ""),
        authorization_phrase=args.authorization_phrase,
        repository_root=Path(__file__).resolve().parents[2],
        max_candles=args.max_candles,
        host=args.host,
        timeout_seconds=args.timeout_seconds,
    )


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        result = _run_command(args)
    except Exception as exc:
        print(
            json.dumps(
                {"status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)},
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
