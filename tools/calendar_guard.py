#!/usr/bin/env python3
"""
BotA Calendar Guard v5
======================
PRIMARY:  TradingEconomics guest access (free, no key needed)
FALLBACK: RapidAPI Global Economic Calendar (RAPIDAPI_CALENDAR_KEY)

Blocks signals around HIGH/MEDIUM impact events for pair currencies.
Provider failure remains fail-open, but trusted-time failure is fail-closed:
an event window cannot be evaluated safely from an untrusted Android clock.

Exit codes:
  0 = safe to trade
  1 = hard block (event window or trusted clock unavailable)

Usage:
  python3 tools/calendar_guard.py --pair EURUSD
  python3 tools/calendar_guard.py --pair EURUSD --json
  python3 tools/calendar_guard.py --pair EURUSD --now-epoch 1786000000
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request

from trusted_time import TrustedTimeUnavailable, trusted_epoch, trusted_iso_z

# ── Config ────────────────────────────────────────────────────────────────────
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_CALENDAR_KEY", "")
RAPIDAPI_HOST = "global-economic-calendar-api-multi-language.p.rapidapi.com"
RAPIDAPI_URL = f"https://{RAPIDAPI_HOST}/api/v1/economic-calendar/events"

TE_URL = "https://api.tradingeconomics.com/calendar"
TE_CREDS = "guest:guest"

# Country → currency mapping
COUNTRY_CURRENCY = {
    "United States": "USD",
    "Euro Area": "EUR",
    "Eurozone": "EUR",
    "European Union": "EUR",
    "Germany": "EUR",
    "France": "EUR",
    "Italy": "EUR",
    "Spain": "EUR",
    "Netherlands": "EUR",
    "United Kingdom": "GBP",
    "Japan": "JPY",
    "Australia": "AUD",
    "Canada": "CAD",
    "Switzerland": "CHF",
    "New Zealand": "NZD",
    "China": "CNY",
}

# Pair → currencies to watch
PAIR_CURRENCIES = {
    "EURUSD": {"EUR", "USD"},
    "GBPUSD": {"GBP", "USD"},
    "USDJPY": {"USD", "JPY"},
    "AUDUSD": {"AUD", "USD"},
    "USDCAD": {"USD", "CAD"},
    "USDCHF": {"USD", "CHF"},
    "EURJPY": {"EUR", "JPY"},
    "GBPJPY": {"GBP", "JPY"},
}

# Block windows (minutes before/after event)
HARD_BLOCK = {
    "high": {"before": 30, "after": 60},
    "medium": {"before": 15, "after": 30},
}

# Keywords that always force high impact treatment
HIGH_KEYWORDS = [
    "non-farm",
    "nfp",
    "payroll",
    "fomc",
    "federal reserve",
    "fed interest rate",
    "interest rate decision",
    "inflation rate",
    "cpi",
    "gdp",
    "bank of england",
    "boe",
    "ecb rate",
    "unemployment rate",
    "housing starts",
]


# ── Provider 1: TradingEconomics ──────────────────────────────────────────────
def fetch_te_events() -> list:
    """Fetch HIGH impact events from TradingEconomics guest API."""
    try:
        params = urllib.parse.urlencode(
            {
                "c": TE_CREDS,
                "importance": "3",  # HIGH only — reduces payload
            }
        )
        req = urllib.request.Request(
            f"{TE_URL}?{params}",
            headers={"User-Agent": "Mozilla/5.0 (Linux; Android 13; Termux)"},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())

        if not isinstance(data, list):
            return []

        normalized = []
        for event in data:
            country = event.get("Country", "")
            currency = event.get("Currency", "") or COUNTRY_CURRENCY.get(
                country, ""
            )
            if not currency:
                continue

            date_str = event.get("Date", "")
            try:
                dt = datetime.datetime.strptime(
                    date_str[:19], "%Y-%m-%dT%H:%M:%S"
                )
                dt = dt.replace(tzinfo=datetime.timezone.utc)
                ts = dt.timestamp()
            except Exception:
                continue

            normalized.append(
                {
                    "title": event.get("Event", ""),
                    "currency": currency,
                    "importance": "high",  # TE importance=3 = HIGH
                    "timestamp": ts,
                    "source": "tradingeconomics",
                }
            )
        return normalized

    except Exception as exc:
        sys.stderr.write(f"[CALENDAR] TE error: {exc}\n")
        return []


# ── Provider 2: RapidAPI fallback ─────────────────────────────────────────────
def fetch_rapidapi_events(currencies: set) -> list:
    """Fetch events from RapidAPI as fallback."""
    if not RAPIDAPI_KEY:
        return []

    currency_to_country = {
        "USD": "US",
        "EUR": "EU",
        "GBP": "GB",
        "JPY": "JP",
        "AUD": "AU",
        "CAD": "CA",
        "CHF": "CH",
        "NZD": "NZ",
    }
    country_to_currency = {v: k for k, v in currency_to_country.items()}
    country_codes = [
        currency_to_country[c]
        for c in currencies
        if c in currency_to_country
    ]

    try:
        params = urllib.parse.urlencode(
            {
                "country_codes": ",".join(country_codes),
                "language": "en",
            }
        )
        req = urllib.request.Request(
            f"{RAPIDAPI_URL}?{params}",
            headers={
                "Content-Type": "application/json",
                "x-rapidapi-host": RAPIDAPI_HOST,
                "x-rapidapi-key": RAPIDAPI_KEY,
            },
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())

        normalized = []
        for event in data.get("data", []):
            currency = event.get("currency", "") or country_to_currency.get(
                event.get("country_code", ""), ""
            )
            if not currency:
                continue

            occ_time = event.get("occurrence_time", "")
            try:
                dt = datetime.datetime.strptime(
                    occ_time[:19], "%Y-%m-%dT%H:%M:%S"
                )
                dt = dt.replace(tzinfo=datetime.timezone.utc)
                ts = dt.timestamp()
            except Exception:
                continue

            importance = event.get("importance", "LOW").lower()
            normalized.append(
                {
                    "title": event.get("localization", {}).get(
                        "long_name", ""
                    ),
                    "currency": currency,
                    "importance": importance,
                    "timestamp": ts,
                    "source": "rapidapi",
                }
            )
        return normalized

    except Exception as exc:
        sys.stderr.write(f"[CALENDAR] RapidAPI error: {exc}\n")
        return []


# ── Event checker ─────────────────────────────────────────────────────────────
def check_events(events: list, currencies: set, now_ts: float) -> dict:
    """Evaluate event windows relative to one trusted UTC epoch.

    ``minutes_away`` is positive before an event and negative after it. Keep
    the configured before/after windows asymmetric in the documented direction.
    """
    result = {
        "block": False,
        "soft_warning": False,
        "penalty_points": 0,
        "reason": "clear",
        "nearest_event": "",
        "minutes_away": 9999.0,
    }

    for event in events:
        currency = event.get("currency", "")
        if currency not in currencies:
            continue

        ts = event.get("timestamp", 0)
        importance = event.get("importance", "low")
        title = event.get("title", "")
        title_lower = title.lower()

        minutes_away = (ts - now_ts) / 60.0

        if abs(minutes_away) < abs(result["minutes_away"]):
            result["minutes_away"] = round(minutes_away, 1)
            result["nearest_event"] = (
                f"{currency} '{title}' ({minutes_away:+.0f}m)"
            )

        is_high_kw = any(kw in title_lower for kw in HIGH_KEYWORDS)
        effective = "high" if is_high_kw else importance.lower()

        if effective in HARD_BLOCK:
            rules = HARD_BLOCK[effective]
            in_before = 0 <= minutes_away <= rules["before"]
            in_after = -rules["after"] <= minutes_away < 0
            if in_before or in_after:
                direction = "before" if minutes_away >= 0 else "after"
                result["block"] = True
                result["reason"] = (
                    f"{effective.upper()} {currency} '{title}' "
                    f"{abs(minutes_away):.0f}min {direction}"
                )
                return result

    return result


def clock_unavailable_result(pair: str, reason: str) -> dict:
    """Return a fail-closed result when UTC event time is not trustworthy."""
    return {
        "block": True,
        "soft_warning": False,
        "penalty_points": 0,
        "reason": f"CLOCK_UNAVAILABLE:{reason}",
        "nearest_event": "",
        "minutes_away": 9999.0,
        "pair": pair,
        "events_checked": 0,
        "source": "none",
        "checked_at": "unavailable",
        "time_source": "none",
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="BotA Calendar Guard v5")
    ap.add_argument("--pair", required=True)
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--now-epoch",
        help="explicit trusted UTC epoch for deterministic replay/tests",
    )
    args = ap.parse_args()

    pair = args.pair.upper().replace("/", "").replace("_", "")
    currencies = PAIR_CURRENCIES.get(pair)

    if not currencies:
        out = {
            "block": False,
            "reason": f"unknown_pair_{pair}",
            "pair": pair,
        }
        if args.json:
            print(json.dumps(out))
        sys.exit(0)

    try:
        now_ts = float(trusted_epoch(args.now_epoch))
        checked_at = trusted_iso_z(args.now_epoch)
    except TrustedTimeUnavailable as exc:
        result = clock_unavailable_result(pair, str(exc))
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"BLOCK: {result['reason']}")
        sys.exit(1)

    events = fetch_te_events()
    source_used = "tradingeconomics"

    if not events:
        events = fetch_rapidapi_events(currencies)
        source_used = "rapidapi" if events else "none"

    result = check_events(events, currencies, now_ts)
    result["pair"] = pair
    result["events_checked"] = len(events)
    result["source"] = source_used
    result["checked_at"] = checked_at
    result["time_source"] = (
        "explicit_epoch" if args.now_epoch is not None else "server_epoch"
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["block"]:
            print(f"BLOCK: {result['reason']}")
        elif result["soft_warning"]:
            print(f"WARN: {result['reason']}")
        else:
            near = result["nearest_event"] or "none"
            print(
                f"CLEAR: {pair} safe via {source_used} "
                f"({result['events_checked']} events, nearest: {near})"
            )

    sys.exit(1 if result["block"] else 0)


if __name__ == "__main__":
    main()
