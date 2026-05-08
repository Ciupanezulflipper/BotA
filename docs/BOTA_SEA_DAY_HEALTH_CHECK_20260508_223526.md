# BotA Sea-Day Health Check

Date recorded UTC: 2026-05-08T22:35:26Z

## Context

User ran health check during a sea day before Sydney, with ship/device time changes active and more time changes expected.

## Result

- Crond exact check: PASS
- Market gate uses server UTC: PASS
- Market gate output: Closed
- Reason: server UTC was after 20:00 UTC
- Cache freshness: PASS
- Watcher server clock: PASS
- Watcher reached scoring/filter: PASS
- Stale skip: NO
- Strategy changed: NO

## Key proof

Market gate debug showed:

```text
server_utc=2026-05-07T21:35:23Z
after 20:00 UTC -> Closed
```

Cache candles:

```text
EURUSD_M15 last_candle_utc=2026-05-07T21:15:00Z
GBPUSD_M15 last_candle_utc=2026-05-07T21:15:00Z
```

Watcher dry run:

```text
server_clock_ok
EURUSD M15 rejected_by_filter score=0.00
GBPUSD M15 rejected_by_filter score=0.00
manual --once scan complete
```

## Interpretation

BotA is no longer controlled by ship/Android clock drift for the two critical gates:

1. Candle freshness in `tools/signal_watcher_pro.sh`
2. Market/session gate in `tools/market_open.sh`

The bot correctly refuses to run outside the configured UTC session and correctly reaches scoring when run manually.

## Next monitoring point

During the next valid server UTC window, expected cron behavior is:

- market gate returns Open
- watcher runs automatically
- stale skip remains absent
- filter/scoring appears in `logs/cron.signals.log`
