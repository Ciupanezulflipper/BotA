# BotA Runtime Validation After Ship-Clock Fix

Date UTC: 2026-05-07T06:24:52Z

## Status

The previous local-phone-clock blocker has been fixed in `tools/signal_watcher_pro.sh` and committed to GitHub.

## Proven successful validation

Latest runtime validation proved:

- `PASS_SERVER_CLOCK=pass`
- `manual_updater_exit_code=0`
- `PASS_CACHE_FRESHNESS=pass`
- `fresh_m15_cache_count_le_2700=3`
- `PASS_WATCHER_SERVER_CLOCK=pass`
- `PASS_WATCHER_REACHED_SCORING=pass`
- `WATCHER_STALE_PRESENT=no`

## Exact results from successful run

After manual updater:

- EURUSD M15 cache last candle: `2026-05-07T03:45:00Z`
- GBPUSD M15 cache last candle: `2026-05-07T03:45:00Z`
- USDJPY M15 cache last candle: `2026-05-07T03:45:00Z`
- Age vs server: `1481s`
- Freshness threshold: `2700s`

Watcher dry run reached filter/scoring:

- EURUSD M15 rejected by filter: `direction_not_tradeable | score<65 | rr<=0 | macro6=3`
- GBPUSD M15 rejected by filter: `direction_not_tradeable | score<65 | rr<=0 | macro6=3`

This is a correct fail-safe result, not a stale-cache failure.

## Important correction

A prior `PASS_CROND=pass` result was not fully reliable because `pgrep -af crond` matched the report/log command name containing the word `crond`.

Future cron checks must use:

```bash
pgrep -x crond
```

## Remaining production checks

1. Exact crond process must be confirmed with `pgrep -x crond`.
2. `tools/market_open.sh` must be verified because cron still uses it before launching the watcher.
3. If `market_open.sh` fails while server UTC says market should be open, then market gate needs a separate server-clock patch.

## Strategy status

- Strategy changed: NO
- Thresholds changed: NO
- Scoring changed: NO
- Telegram routing changed: NO
- Supabase changed: NO
