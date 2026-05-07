# BotA Market Open Server-Clock Patch

Date UTC: 2026-05-07T06:34:51Z

## Summary

`tools/market_open.sh` was patched to use trusted server UTC instead of Android/device UTC.

## Reason

The ship/Android clock is currently wrong by around +7116 seconds because of manual sea-day ship time adjustments.

Before this patch, `market_open.sh` used:

```bash
TZ=UTC date
```

That still depends on the Android system clock, so the market gate could open around two hours early.

## Preserved behavior

The trading session rule was not changed:

- Open only Monday-Friday.
- Active session: `07:00-20:00 UTC`.
- Saturday/Sunday closed.
- Friday after `20:00 UTC` closed.
- `SKIP_SESSION_FILTER=1` still bypasses only session-hour filtering, not weekend/Friday close.

## Safety behavior

If server UTC cannot be computed reliably:

- Output: `Closed`
- Exit code: `1`
- Fail-closed behavior.

## Strategy status

- Strategy changed: NO
- Scoring changed: NO
- Thresholds changed: NO
- Watcher changed in this step: NO
