# Historical Candle Acquisition Audit — 2026-08-07

Recorded: **2026-08-07 20:45 UTC**

## Objective

Close the verified replay-input gap without touching BotA's rolling production candle cache.

Required replay interval:

```text
2026-06-01T00:00:00Z <= candle_time < 2026-08-01T00:00:00Z
```

Scope:

```text
EURUSD: M15 H1 H4 D1
GBPUSD: M15 H1 H4 D1
```

## Why isolated acquisition is required

The production fetcher uses OANDA `count=500` and writes `data/candles/<PAIR>_<TF>.csv`. Phone evidence at 2026-08-07 19:10:26 UTC shows:

```text
M15 retained from 2026-07-31
H1  retained from 2026-07-10
H4  covers June-July
D1  covers June-July
```

Standalone M15 files cover only 2026-02-27 through 2026-03-06.

Therefore current retained local inputs cannot support a full June-July replay.

The historical collector writes only below:

```text
data/replay/<dataset-id>/
```

It never writes the production candle cache.

## PR #6 salvage decision

Draft PR #6 contains valuable historical-replay design work but is not an integration source for current `main`.

Verified GitHub facts:

```text
PR=6
STATE=OPEN_DRAFT
MERGEABLE=FALSE
CHANGED_FILES=129
CURRENT_HEAD=b0212697ed410b6a12d6634e71915ab6fe092061
CURRENT_HEAD_SECURITY_SCAN=PASS
CURRENT_HEAD_HISTORICAL_REPLAY_WORKFLOW=PASS
```

Its changed-file list includes the sidecar plus out-of-scope canonical/runtime paths. Do not merge or cherry-pick PR #6 wholesale.

Only validated architectural ideas were reused: explicit historical ranges, bounded chunking, raw evidence preservation, immutable output, checksums, path containment, and fail-closed validation.

## Production contract mapped into the collector

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

Authentication names match production:

```text
OANDA_API_TOKEN
OANDA_API_URL
```

`.env` is parsed as data, never shell-executed.

Approved origins:

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
- at most three HTTP attempts per chunk;
- retries only for HTTP 429 or 5xx;
- bounded exponential backoff: 0.5 s then 1.0 s;
- every retry response preserved using attempt-suffixed raw/metadata filenames;
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
- secondary failure-marker write errors reported without masking the original error;
- no Telegram, Supabase, order placement, strategy, service, cron, or production-cache mutation.

## Focused validation

Offline validation after DeepSource and CodeRabbit feedback:

```text
TESTS=11
PASSED=11
FAILED=0
PYTHON_COMPILE=PASS
REAL_PROVIDER_CALLS=0
TELEGRAM_CALLS=0
SUPABASE_CALLS=0
```

Coverage includes:

- production OANDA pair/timeframe/request mapping;
- bounded chunk planning;
- exclusion of incomplete candles;
- equal-value/separate-object boundary deduplication;
- conflicting duplicate rejection;
- preview non-mutation;
- immutable datasets plus unchanged manifest on rejected rerun;
- manifest artifact checksums;
- non-retryable HTTP failure evidence;
- retryable `503 -> 429 -> 200` recovery with exact backoff and all attempts preserved;
- safe `.env` parsing;
- OANDA scheme/host/credential/path/custom-port restrictions;
- path escape and overlength dataset-id rejection.

## External review findings and disposition

PR #57 received DeepSource and CodeRabbit review.

DeepSource initially found:
- one Python type-check issue;
- one unused test import;
- two collapsible test context-manager findings;
- one complexity warning.

The major findings were corrected. The collector was also split into helpers to reduce acquisition-function complexity.

CodeRabbit's substantive finding was missing bounded retry/backoff for 429 and 5xx. This was implemented with attempt-by-attempt evidence preservation and a dedicated deterministic test.

Additional valid CodeRabbit hygiene recommendations incorporated:
- `actions/checkout` uses `persist-credentials: false`;
- workflow push validation targets `main`, not the temporary feature branch;
- custom-port and overlength-ID branches are tested;
- rejected immutable rerun proves the original manifest is unchanged;
- boundary dedup test proves equality rather than object identity;
- successive-candle iteration uses `itertools.pairwise`;
- failure-marker write errors are reported;
- dataset-ID validation is shared;
- the exact acquisition command is recorded.

Merge remains conditional on exact final PR-head CI/security checks passing.

## Dataset contract

Successful layout:

```text
data/replay/<dataset-id>/
  raw/<PAIR>/<TF>/chunk-####-attempt-##.json
  metadata/<PAIR>/<TF>/chunk-####-attempt-##.json
  candles/<PAIR>_<TF>.csv
  manifest.json
```

`manifest.json` records provider, midpoint contract, requested interval, pair/timeframe scope, per-stream request and HTTP-attempt counts, rows, coverage/gaps, and artifact SHA-256 checksums.

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

## Next acceptance step after merge

Acquire exactly one credential-gated dataset:

```text
dataset-id=oanda-20260601-20260801-20260807
start=2026-06-01T00:00:00Z
end-exclusive=2026-08-01T00:00:00Z
pairs=EURUSD GBPUSD
timeframes=M15 H1 H4 D1
```

Then verify `manifest.json` and artifact hashes. Only after dataset integrity passes should the deterministic production-semantics replay be built and run.
