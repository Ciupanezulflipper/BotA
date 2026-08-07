# Historical Acquisition Reconciliation — 2026-08-07

Recorded: **2026-08-07 21:00 UTC**

## Trigger

Two independent current-`main` branches solved the same verified historical-candle gap at nearly the same time:

- PR #57 — `feat: add immutable historical candle acquisition`
- PR #58 — `audit: salvage immutable historical candle acquisition`

PR #57 merged first at `2026-08-07T20:57:29Z` as `87f51a438d363daf0e025b2c1fae8e9c935f1c0b`.
PR #58 merged 23 seconds later at `2026-08-07T20:57:52Z` as `9e96815c901e13b72644e0a759175ed80abb6ca2`.

This created two historical-candle acquisition implementations on `main`. Keeping both would create operator ambiguity and unnecessary maintenance risk.

## Canonical decision

Keep **PR #57** as the single historical acquisition path:

```text
tools/fetch_historical_candles.py
```

Reasons:

- uses BotA's production pair/timeframe naming and OANDA midpoint contract;
- writes production-compatible five-column candle CSVs;
- preview/no-network is the default;
- real provider GETs require explicit `--execute`;
- safely resolves `OANDA_API_TOKEN` and `OANDA_API_URL` without executing `.env`;
- bounds request size, timeout, and response size;
- retries only HTTP 429/5xx with bounded exponential backoff;
- preserves every raw retry response and redacted metadata;
- validates chunk-window membership and final half-open range;
- reconciles exact boundary duplicates and rejects conflicts;
- records coverage/gap statistics;
- emits immutable dataset manifests with SHA-256/byte-size artifact records;
- preserves `FAILED.json` if acquisition fails after dataset creation;
- focused offline tests and the dedicated acquisition workflow passed on exact PR #57 head;
- SonarCloud Quality Gate passed on exact PR #57 head;
- CodeRabbit and DeepSource findings were addressed before merge;
- canonical continuity/audit documentation already points to this tool.

## Removed duplicate

The following PR #58-only paths are removed by the reconciliation cleanup:

```text
.github/workflows/historical-acquisition-20260807.yml
audit/historical_acquisition_20260807/README.md
audit/historical_acquisition_20260807/__init__.py
audit/historical_acquisition_20260807/acquire.py
tests/test_historical_acquisition_20260807.py
```

PR #58 remains useful repository history showing the independently validated design, but it is not an operational path after this cleanup.

## Additional containment

`data/replay/` is added to `.gitignore` before any live historical acquisition. The canonical collector intentionally writes immutable replay datasets below `data/replay/<dataset-id>/`; those potentially large provider artifacts must never be accidentally committed.

## Production mutation status

```text
PHONE_RUNTIME_CHANGED=NO
LIVE_CANDLE_CACHE_CHANGED=NO
STRATEGY_CHANGED=NO
THRESHOLDS_CHANGED=NO
PAIR_UNIVERSE_CHANGED=NO
TELEGRAM_CHANGED=NO
SUPABASE_CHANGED=NO
SERVICE_OR_CRON_CHANGED=NO
REAL_PROVIDER_CALL_PERFORMED=NO
```

## Exactly one next operational action

After this cleanup is merged, run the canonical collector in **preview mode only** on the phone for the frozen replay interval and inspect the compact request plan before permitting any OANDA historical GETs.
