#!/usr/bin/env python3
"""Trusted UTC helpers for BotA market and strategy semantics.

Production market/session decisions must never derive "now" from Android wall
clock. The outer watcher gate establishes ``BOTA_SERVER_EPOCH`` from multiple
server Date headers and child components reuse that immutable cycle instant.

CLOCK_BOOTTIME/monotonic time remains the correct domain for cadence, cooldowns,
and same-boot health; this module is intentionally only for UTC event semantics.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Mapping

MIN_TRUSTED_EPOCH = 1_000_000_000
UTC = timezone.utc


class TrustedTimeUnavailable(RuntimeError):
    """Raised when no structurally valid trusted UTC epoch is available."""


def parse_epoch(value: object) -> int | None:
    """Return a validated epoch integer, or ``None`` for invalid input."""
    if value is None or isinstance(value, bool):
        return None
    try:
        text = str(value).strip()
        if not text or not text.isdigit():
            return None
        epoch = int(text)
    except (TypeError, ValueError, OverflowError):
        return None
    return epoch if epoch > MIN_TRUSTED_EPOCH else None


def trusted_epoch(
    explicit_epoch: object | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    """Resolve trusted strategy/event time without falling back to wall clock.

    An explicit epoch is useful for deterministic replay/tests. Production
    callers normally inherit ``BOTA_SERVER_EPOCH`` from ``watcher_gated_cycle``.
    Invalid explicit input is rejected rather than silently using another time
    source, preventing test/replay mistakes from being masked.
    """
    if explicit_epoch is not None:
        epoch = parse_epoch(explicit_epoch)
        if epoch is None:
            raise TrustedTimeUnavailable("invalid_explicit_epoch")
        return epoch

    env = os.environ if environ is None else environ
    epoch = parse_epoch(env.get("BOTA_SERVER_EPOCH"))
    if epoch is None:
        raise TrustedTimeUnavailable("BOTA_SERVER_EPOCH_unavailable")
    return epoch


def trusted_utc(
    explicit_epoch: object | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> datetime:
    """Return an aware UTC datetime from trusted epoch input only."""
    epoch = trusted_epoch(explicit_epoch, environ=environ)
    return datetime.fromtimestamp(epoch, UTC)


def session_component(
    explicit_epoch: object | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> tuple[float, str]:
    """Return the existing BotA session score/tag at trusted UTC time.

    The score values and fixed UTC windows are deliberately unchanged here:
    12:00-16:00 overlap = +5; London/NY-only windows = +2; edges = 0.
    This package changes the source of time, not strategy calibration.
    """
    now_utc = trusted_utc(explicit_epoch, environ=environ)
    hour = now_utc.hour + now_utc.minute / 60.0
    if 12.0 <= hour < 16.0:
        return 5.0, "session_overlap"
    if 7.0 <= hour < 12.0:
        return 2.0, "session_london"
    if 16.0 <= hour < 20.0:
        return 2.0, "session_ny"
    return 0.0, "session_edge"


def trusted_iso_z(
    explicit_epoch: object | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Return trusted UTC as an ISO-8601 ``Z`` timestamp."""
    return trusted_utc(explicit_epoch, environ=environ).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
