from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

SENSITIVE_RESPONSE_HEADERS = {"set-cookie", "www-authenticate", "proxy-authenticate"}


@dataclass(frozen=True)
class ResponseMetadata:
    status: int
    headers: dict[str, str]
    request_id: str | None
    content_type: str | None


def capture_response_metadata(status: int, headers: Mapping[str, str]) -> ResponseMetadata:
    if status < 100 or status > 599:
        raise ValueError("invalid HTTP status")

    cleaned: dict[str, str] = {}
    for key, value in headers.items():
        key_s = str(key)
        cleaned[key_s] = (
            "[REDACTED]"
            if key_s.lower() in SENSITIVE_RESPONSE_HEADERS
            else str(value)
        )

    lowered = {key.lower(): value for key, value in cleaned.items()}
    return ResponseMetadata(
        status=status,
        headers=dict(sorted(cleaned.items(), key=lambda item: item[0].lower())),
        request_id=lowered.get("requestid") or lowered.get("x-request-id"),
        content_type=lowered.get("content-type"),
    )
