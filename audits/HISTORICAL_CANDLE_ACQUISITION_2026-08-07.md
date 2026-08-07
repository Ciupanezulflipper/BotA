# Historical Candle Acquisition Audit — 2026-08-07

Recorded: **2026-08-07 20:20 UTC**

## Objective

Close the verified replay-input gap without touching BotA's rolling production candle cache.

The required replay interval is the half-open range:

```text
2026-06-01T00:00:00Z <= candle_time < 2026-08-01T00:00:00Z
```

Pairs and timeframes:

```text
EURUSD: M15 H1 H4 D1
GBPUSD: M15 H1 H4 D1
```

## Why a new isolated collector is required

The current production fetcher uses OANDA `count=500` and writes `data/candles/<PAIR>_<TF>.csv`. Verified phone retention is insufficient for a June-July replay:

```text
M15 retained from 2026-07-31
H1  retained from 2026-07-10
H4  covers June-July
D1  covers June-July
```

The historical collector therefore writes only below:

```text
data/replay/<dataset-id>/
```

It never uses the production cache path.

## PR #6 salvage decision

Draft PR #6 contains valuable historical-replay design work, but it is not an integration source for current `main`.

Verified GitHub facts on 2026-08-07:

```text
PR=6
STATE=OPEN_DRAFT
MERGEABLE=FALSE
CHANGED_FILES=129
CURRENT_HEAD=b0212697ed410b6a12d6634e71915ab6fe092061
CURRENT_HEAD_SECURITY_SCAN=PASS
CURRENT_HEAD_HISTORICAL_REPLAY_WORKFLOW=PASS
```

The changed-file list includes the isolated sidecar but also canonical/runtime paths such as `CONTINUITY.md`, `DECISIONS.md`, `RESOLVED.md`, `state/STATE.json`, and `tools/heartbeat.sh`. PR #6 must not be merged or cherry-picked wholesale.

Only its proven design ideas were reused: explicit historical ranges, bounded chunking, raw evidence preservation, immutable output, checksums, path containment, and fail-closed validation.

## Current production contract mapped into the collector

The new collector preserves the relevant production OANDA contract:

```text
provider=OANDA
price=M
EURUSD -> EUR_USD
GBPUSD -> GBP_USD
M15 -> M15
H1  -> H1
H4  -> H4
D1  -> D
complete_candles_only=YES
```

Authentication uses the same names as production:

```text
OANDA_API_TOKEN
OANDA_API_URL
```

`.env` is parsed as data by the Python collector; it is not shell-sourced or executed.

Approved origins are restricted to:

```text
https://api-fxpractice.oanda.com
https://api-fxtrade.oanda.com
```

## Safety and integrity properties

`tools/fetch_historical_candles.py` provides:

- preview/no-network mode by default;
- network acquisition only with explicit `--execute`;
- explicit `from`/`to` requests with no `count` parameter;
- bounded requests below OANDA's 5000-candle request limit;
- bounded HTTP response size and timeout;
- raw provider JSON persisted before semantic validation;
- redacted request/response metadata;
- complete midpoint candles only;
- OHLC validity checks;
- exact duplicate boundary reconciliation and conflicting-duplicate rejection;
- final half-open requested range filtering;
- production-compatible five-column candle CSVs;
- immutable dataset IDs: an existing dataset is never overwritten;
- SHA-256 and byte-size records for every persisted data artifact;
- `FAILED.json` preservation when acquisition fails after dataset creation;
- no Telegram, Supabase, order placement, strategy, service, cron, or production-cache mutation.

## Validation before GitHub integration

Focused offline tests were executed without provider credentials or network access:

```text
TESTS=10
PASSED=10
FAILED=0
PYTHON_COMPILE=PASS
REAL_PROVIDER_CALLS=0
TELEGRAM_CALLS=0
SUPABASE_CALLS=0
```

The focused tests cover request mapping, bounded chunking, incomplete candles, boundary reconciliation, preview non-mutation, immutable datasets, manifest checksums, failed-HTTP evidence preservation, safe `.env` handling, OANDA origin allowlisting, and path-escape rejection.

The dedicated GitHub workflow is an additional merge gate and also proves that preview mode creates no `data/replay/ci-preview` dataset.

## Dataset contract

A successful dataset has this high-level layout:

```text
data/replay/<dataset-id>/
  raw/<PAIR>/<TF>/chunk-*.json
  metadata/<PAIR>/<TF>/chunk-*.json
  candles/<PAIR>_<TF>.csv
  manifest.json
```

`manifest.json` records provider, midpoint price contract, requested interval, pair/timeframe scope, per-stream rows/request counts/coverage/gaps, and artifact SHA-256 checksums.

## Production mutation status

```text
STRATEGY_CHANGED=NO
THRESHOLDS_CHANGED=NO
PAIR_UNIVERSE_CHANGED=NO
COOLDOWN_CHANGED=NO
LIVE_FETCHER_CHANGED=NO
PRODUCTION_CACHE_CHANGED=NO
SERVICE_OR_CRON_CHANGED=NO
PROVIDER_CALL_PERFORMED_DURING_REPOSITORY_IMPLEMENTATION=NO
```

## Next acceptance step

After this package is merged, run exactly one credential-gated phone acquisition for:

```text
dataset-id=oanda-20260601-20260801-20260807
start=2026-06-01T00:00:00Z
end-exclusive=2026-08-01T00:00:00Z
pairs=EURUSD GBPUSD
timeframes=M15 H1 H4 D1
```

Then verify `manifest.json` and artifact hashes. Only after the dataset passes integrity checks should the deterministic production-semantics replay be built/run.
