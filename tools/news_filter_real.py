from __future__ import annotations

from datetime import datetime, timezone, timedelta
import http.client
import json
import os
from typing import Tuple
from urllib.parse import urlencode

from trusted_time import TrustedTimeUnavailable, trusted_utc

UTC = timezone.utc
FINNHUB_HOST = "finnhub.io"
FINNHUB_PATH = "/api/v1/calendar/economic"

# Basic symbol → currency map (extend as needed)
PAIR_TO_CCY = {
    "EURUSD": ["EUR", "USD"],
    "GBPUSD": ["GBP", "USD"],
    "USDJPY": ["USD", "JPY"],
    "XAUUSD": ["USD"],  # gold => USD-sensitive
}


def _needs_block(imp: str) -> bool:
    return imp.lower() in {"high", "red", "3", "3_high"}


def _fetch_finnhub_calendar(
    start: str,
    end: str,
    key: str,
    timeout: int,
) -> dict:
    """Fetch Finnhub calendar over a fixed HTTPS endpoint only."""
    query = urlencode({"from": start, "to": end, "token": key})
    connection = http.client.HTTPSConnection(FINNHUB_HOST, timeout=timeout)
    try:
        connection.request(
            "GET",
            f"{FINNHUB_PATH}?{query}",
            headers={"Accept": "application/json", "User-Agent": "BotA/1.0"},
        )
        response = connection.getresponse()
        raw = response.read()
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"finnhub_http_{response.status}")
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    finally:
        connection.close()


def news_risk_gate(
    pair: str,
    now: datetime | None = None,
    window_min: int = 60,
) -> Tuple[bool, str]:
    """Return whether trading may proceed through the Finnhub news gate.

    Explicit ``now`` is retained for deterministic replay/tests. Production
    derives the calendar date from ``BOTA_SERVER_EPOCH`` and never falls back to
    Android wall time. Provider/API failure behavior is intentionally unchanged:
    unavailable calendar data warns but does not hard-block. Trusted-time
    failure is different — with an active calendar API, the event date cannot be
    classified safely, so the gate fails closed.
    """
    if os.getenv("NEWS_BLOCK_ENABLED", "true").lower() != "true":
        return True, "news_filter_disabled"

    key = os.getenv("FINNHUB_API_KEY", "")
    if not key:
        return True, "no_calendar_api"

    if now is None:
        try:
            now = trusted_utc()
        except TrustedTimeUnavailable:
            return False, "clock_unavailable"
    else:
        now = now.astimezone(UTC)

    start = (now - timedelta(minutes=window_min)).strftime("%Y-%m-%d")
    end = (now + timedelta(minutes=window_min)).strftime("%Y-%m-%d")

    try:
        data = _fetch_finnhub_calendar(
            start,
            end,
            key,
            int(os.getenv("HTTP_TIMEOUT_SEC", "8")),
        )
        events = data.get("economicCalendar", [])
        watch_ccy = PAIR_TO_CCY.get(pair.upper(), [])
        for event in events:
            currency = (event.get("currency") or "").upper()
            impact = str(event.get("impact") or "").lower()
            # Finnhub exposes date-level calendar data here. Preserve the
            # existing conservative behavior: matching high-impact currency
            # events on the queried UTC day block the pair.
            if currency in watch_ccy and _needs_block(impact):
                return False, f"red_news_{currency}"
        return True, "no_red_news"
    except Exception:
        # Provider failure policy is unchanged: do not hard-block solely because
        # Finnhub is unavailable.
        return True, "calendar_unavailable"
