from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .path_guard import ensure_within_root
from .request_metadata import build_request_metadata
from .response_metadata import capture_response_metadata

OANDA_PRACTICE_BASE = "https://api-fxpractice.oanda.com"
OANDA_LIVE_BASE = "https://api-fxtrade.oanda.com"
_ALLOWED_BASES = {OANDA_PRACTICE_BASE, OANDA_LIVE_BASE}


@dataclass(frozen=True)
class TransportResponse:
    status: int
    headers: dict[str, str]
    body: bytes


Transport = Callable[[str, Mapping[str, str], float], TransportResponse]


def _default_transport(url: str, headers: Mapping[str, str], timeout_seconds: float) -> TransportResponse:
    request = Request(url=url, method="GET", headers=dict(headers))
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310: URL is allowlisted before use
            return TransportResponse(
                status=int(response.status),
                headers={str(k): str(v) for k, v in response.headers.items()},
                body=response.read(),
            )
    except HTTPError as exc:
        return TransportResponse(
            status=int(exc.code),
            headers={str(k): str(v) for k, v in exc.headers.items()},
            body=exc.read(),
        )
    except URLError as exc:
        raise ConnectionError(f"OANDA request failed: {exc.reason}") from exc


def fetch_oanda_chunk(
    *,
    output_root: Path,
    request_path_and_query: str,
    token: str,
    enabled: bool = False,
    base_url: str = OANDA_PRACTICE_BASE,
    timeout_seconds: float = 30.0,
    transport: Transport | None = None,
) -> dict:
    """Fetch one OANDA chunk only when explicitly enabled.

    This function does not read tokens from environment variables and does not
    write provider bytes. The caller must persist the returned bytes through the
    immutable artifact layer.
    """
    if enabled is not True:
        raise PermissionError("live OANDA acquisition is disabled; pass enabled=True explicitly")
    if not token or not token.strip():
        raise ValueError("non-empty OANDA token required")
    if base_url not in _ALLOWED_BASES:
        raise ValueError("unapproved OANDA base URL")
    if timeout_seconds <= 0 or timeout_seconds > 120:
        raise ValueError("timeout_seconds must be within (0, 120]")
    if not request_path_and_query.startswith("/v3/instruments/"):
        raise ValueError("unexpected OANDA request path")
    if "count=" in request_path_and_query:
        raise ValueError("explicit from/to replay requests must not contain count")

    root = output_root.resolve()
    ensure_within_root(root, root)
    root.mkdir(parents=True, exist_ok=True)

    url = f"{base_url}{request_path_and_query}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token.strip()}",
        "User-Agent": "BotA-Historical-Replay-Sidecar/1",
    }
    request_meta = build_request_metadata(method="GET", url=url, headers=headers)
    response = (transport or _default_transport)(url, headers, timeout_seconds)
    response_meta = capture_response_metadata(response.status, response.headers)

    if response.status < 200 or response.status >= 300:
        preview = response.body[:512].decode("utf-8", errors="replace")
        raise RuntimeError(f"OANDA HTTP {response.status}: {preview}")

    try:
        payload = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("OANDA response is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("candles"), list):
        raise ValueError("OANDA response missing candles list")

    return {
        "request": request_meta,
        "response": response_meta,
        "body": response.body,
    }
