# Production Watcher Freshness Parity — 2026-07-11

## Production reference

- [proven] Production reference commit is `fa289ad3f7b6ff430f13609950e5af341aee2e9d`.
- [proven] Production reference file is `tools/signal_watcher_pro.sh`, blob SHA `f065476ec70627e63218796cc4621debd2d631e7`.
- [proven] This increment is static and synthetic; no production script was imported or executed.

## Mapped production semantics

- [proven] Authoritative freshness comes from the last candle timestamp inside `cache/<PAIR>_<TF>.json`.
- [proven] Indicator-file mtime is non-authoritative and only supports a lag warning.
- [proven] Production requires a trusted server-clock epoch and fails closed when it is unavailable.
- [proven] Production accepts either explicit `last_candle_utc` or the last Yahoo-compatible chart timestamp.
- [proven] Negative age is rejected as a future timestamp.
- [proven] Missing, invalid, or unparseable raw-cache timestamps cause a skip.
- [proven] Production marks a candle stale only when `age > CANDLE_MAX_AGE_SECS`.
- [proven] Therefore `age == CANDLE_MAX_AGE_SECS` remains eligible under the production shell contract.
- [proven] The age is measured from the provider candle start timestamp, not its close timestamp.

## Sidecar implementation

- [proven] `src/watcher_freshness.py` now models the production freshness decision as `FRESH`, `STALE`, or `MISSING`.
- [proven] The module preserves decision time, latest candle start, computed age, ceiling, source, and reason.
- [proven] It fails closed on missing trusted clock, missing timestamps, future timestamps, naive datetimes, and non-monotonic input.
- [proven] It uses the exact strict production boundary: stale only when age is greater than the ceiling.

## Synthetic proof coverage

- [proven] Exact ceiling remains fresh.
- [proven] One second beyond the ceiling is stale.
- [proven] Missing timestamp fails closed.
- [proven] Missing trusted clock fails closed.
- [proven] Future timestamp fails closed.
- [proven] Latest candle start is authoritative.
- [proven] Non-monotonic timestamps are rejected.
- [proven] Timezone-naive inputs are rejected.

## Boundary

- [proven] This module reproduces the production watcher freshness gate only.
- [not proven] Historical runtime availability is reconstructed until real watcher/cron outage epochs are preserved and supplied to cycle classification.
- [not proven] Exact production decision parity remains blocked on scoring, quality filtering, H1/H4 fusion ordering, news/calendar gates, pause state, and runtime-epoch evidence.
- [proven] The sidecar remains an isolated verifier and is not a second BotA.
