from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SENSITIVE_HEADERS = {"authorization", "proxy-authorization", "x-api-key", "api-key"}
SENSITIVE_QUERY_KEYS = {"token", "api_key", "apikey", "access_token", "key"}


@dataclass(frozen=True)
class RequestMetadata:
    method: str
    url: str
    headers: dict[str, str]
    body_sha256: str | None
    body_bytes: int


def redact_url(url: str) -> str:
    parts = urlsplit(url)
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        query.append((key, "[REDACTED]" if key.lower() in SENSITIVE_QUERY_KEYS else value))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in headers.items():
        result[str(key)] = "[REDACTED]" if str(key).lower() in SENSITIVE_HEADERS else str(value)
    return dict(sorted(result.items(), key=lambda item: item[0].lower()))


def build_request_metadata(
    *, method: str, url: str, headers: Mapping[str, str], body: bytes | None = None
) -> RequestMetadata:
    payload = body or b""
    return RequestMetadata(
        method=method.upper(),
        url=redact_url(url),
        headers=redact_headers(headers),
        body_sha256=sha256(payload).hexdigest() if body is not None else None,
        body_bytes=len(payload),
    )
