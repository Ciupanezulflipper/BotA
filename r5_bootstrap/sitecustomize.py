"""Fail-closed external side-effect sandbox for BotA R5 VPS observation.

This module is inert unless BOTA_R5_SHADOW=1. In R5 shadow mode it prevents
production Telegram and Supabase writes while allowing the runtime to execute
its normal decision/delivery control flow against deterministic synthetic
responses. Every suppressed write boundary is durably recorded without URLs,
credentials, request bodies, or response payloads.
"""
from __future__ import annotations

import os

if os.environ.get("BOTA_R5_SHADOW") == "1":
    import fcntl
    import http.client
    import io
    import json
    import socket
    import sys
    import time
    import urllib.parse
    import urllib.request
    from datetime import datetime, timezone
    from pathlib import Path
    from typing import Any

R5_SENTINEL = "R5_SHADOW_NO_NETWORK"
SENSITIVE_KEYS = (
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_TOKEN",
    "BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "CHAT_ID",
    "TG_CHAT_ID",
    "SUPABASE_SERVICE_KEY",
    "BOTA_HEALTH_INGEST_SECRET",
)
FORCED_ENV = {
    "TELEGRAM_ENABLED": "1",
    "DRY_RUN_MODE": "false",
    "HEARTBEAT_DRY_RUN": "1",
    "DAILY_SUMMARY_GATE_DRY_RUN": "1",
    "DAILY_SUMMARY_SEND": "0",
    "RUNTIME_HEALTH_PUSH_DRY_RUN": "1",
}


def _blocked_category(host: object) -> str | None:
    if isinstance(host, bytes):
        try:
            host_text = host.decode("ascii", errors="strict")
        except UnicodeDecodeError:
            return None
    else:
        host_text = str(host or "")
    host_text = host_text.strip().lower().rstrip(".")
    if host_text == "api.telegram.org":
        return "telegram"
    if host_text.endswith(".supabase.co"):
        return "supabase"
    return None


def _ledger_path() -> Path:
    root = Path(os.environ.get("BOTA_MUTABLE_ROOT", "/var/lib/bota")).expanduser()
    return root / "state" / "r5_side_effects.jsonl"


def _record(*, transport: str, category: str, method: str, operation: str,
            synthetic_status: int | None) -> None:
    path = _ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "monotonic_ns": time.monotonic_ns(),
        "process": Path(sys.argv[0] or "python").name[:128],
        "pid": os.getpid(),
        "transport": transport,
        "host_category": category,
        "method": str(method or "").upper()[:16],
        "operation": operation,
        "synthetic_status": synthetic_status,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _synthetic_body(category: str, method: str) -> bytes:
    if category == "telegram":
        return b'{"ok":true,"result":{"message_id":-1}}'
    if str(method).upper() == "GET":
        return b"[]"
    return b"{}"


class _UrlopenResponse:
    def __init__(self, body: bytes, status: int = 200):
        self._stream = io.BytesIO(body)
        self.status = status
        self.code = status
        self.headers: dict[str, str] = {}

    def read(self, amt: int = -1) -> bytes:
        return self._stream.read(amt)

    def getcode(self) -> int:
        return self.status

    @staticmethod
    def geturl() -> str:
        return "r5-shadow://suppressed"

    def info(self) -> dict[str, str]:
        return self.headers

    def __enter__(self) -> "_UrlopenResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        self._stream.close()


class _HTTPResponse:
    def __init__(self, body: bytes, status: int = 200):
        self._stream = io.BytesIO(body)
        self.status = status
        self.reason = "R5_SHADOW_SUPPRESSED"
        self.version = 11

    def read(self, amt: int | None = None) -> bytes:
        return self._stream.read(-1 if amt is None else amt)

    @staticmethod
    def getheader(_name: str, default: Any = None) -> Any:
        return default

    @staticmethod
    def getheaders() -> list[tuple[str, str]]:
        return []

    @staticmethod
    def isclosed() -> bool:
        return False

    def close(self) -> None:
        self._stream.close()


def _request_url_and_method(target: object, data: object) -> tuple[str, str]:
    if isinstance(target, urllib.request.Request):
        return target.full_url, target.get_method()
    return str(target), "POST" if data is not None else "GET"


def _install() -> None:
    # Keep opaque callable references so wrappers can forward the exact original
    # call shape without duplicating or narrowing stdlib signatures.
    original_urlopen: Any = urllib.request.urlopen
    original_request: Any = http.client.HTTPSConnection.request
    original_getresponse: Any = http.client.HTTPSConnection.getresponse
    original_getaddrinfo: Any = socket.getaddrinfo

    def guarded_urlopen(url: object, *args: object, **kwargs: object) -> Any:
        data = args[0] if args else kwargs.get("data")
        raw_url, method = _request_url_and_method(url, data)
        host = urllib.parse.urlsplit(raw_url).hostname or ""
        category = _blocked_category(host)
        if category is None:
            return original_urlopen(url, *args, **kwargs)
        body = _synthetic_body(category, method)
        _record(transport="urllib", category=category, method=method,
                operation="suppressed_external_side_effect", synthetic_status=200)
        return _UrlopenResponse(body, 200)

    def guarded_request(connection: http.client.HTTPSConnection,
                        *args: object, **kwargs: object) -> Any:
        method = args[0] if args else kwargs.get("method", "")
        category = _blocked_category(getattr(connection, "host", ""))
        if category is None:
            return original_request(connection, *args, **kwargs)
        response_body = _synthetic_body(category, str(method))
        _record(transport="http.client", category=category, method=str(method),
                operation="suppressed_external_side_effect", synthetic_status=200)
        setattr(connection, "_bota_r5_response", _HTTPResponse(response_body, 200))
        return None

    def guarded_getresponse(connection: http.client.HTTPSConnection,
                            *args: object, **kwargs: object) -> Any:
        response = getattr(connection, "_bota_r5_response", None)
        if response is not None:
            delattr(connection, "_bota_r5_response")
            return response
        return original_getresponse(connection, *args, **kwargs)

    def guarded_getaddrinfo(host: object, *args: object, **kwargs: object) -> Any:
        category = _blocked_category(host)
        if category is not None:
            _record(transport="socket", category=category, method="DNS",
                    operation="blocked_unwrapped_network_path", synthetic_status=None)
            raise socket.gaierror("R5 shadow blocked external side-effect host")
        return original_getaddrinfo(host, *args, **kwargs)

    setattr(urllib.request, "urlopen", guarded_urlopen)
    setattr(http.client.HTTPSConnection, "request", guarded_request)
    setattr(http.client.HTTPSConnection, "getresponse", guarded_getresponse)
    setattr(socket, "getaddrinfo", guarded_getaddrinfo)


if os.environ.get("BOTA_R5_SHADOW") == "1":
    rejected = {
        key for key in SENSITIVE_KEYS
        if os.environ.get(key, "").strip() not in {"", R5_SENTINEL}
    }
    if os.environ.get("BOTA_R5_PRODUCTION_SECRET_PRESENT") == "1":
        rejected.add("PREEXISTING_R5_SECRET_FLAG")
    os.environ["BOTA_R5_PRODUCTION_SECRET_PRESENT"] = "1" if rejected else "0"
    os.environ["BOTA_R5_REJECTED_SECRET_KEYS"] = ",".join(sorted(rejected))
    for key in SENSITIVE_KEYS:
        os.environ[key] = R5_SENTINEL
    for key, forced_value in FORCED_ENV.items():
        os.environ[key] = forced_value
    _install()
    os.environ["BOTA_R5_BOOTSTRAP_ACTIVE"] = "1"
