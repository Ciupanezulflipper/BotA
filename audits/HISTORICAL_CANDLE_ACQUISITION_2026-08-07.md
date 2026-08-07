# Historical Candle Acquisition Audit — 2026-08-07

Recorded: **2026-08-07 23:06 UTC**

## Objective

Close the verified replay-input gap without touching BotA's rolling production candle cache, and preserve a reproducible immutable dataset with enough pre-roll to reconstruct June-July indicators.

Replay evaluation interval:

```text
2026-06-01T00:00:00Z <= decision_time < 2026-08-01T00:00:00Z
```

Raw acquisition interval used for warm-up:

```text
2024-01-01T00:00:00Z <= candle_time < 2026-08-01T00:00:00Z
```

Scope:

```text
EURUSD: M15 H1 H4 D1
GBPUSD: M15 H1 H4 D1
```

## Why isolated acquisition was required

The production fetcher uses OANDA `count=500` and writes `data/candles/<PAIR>_<TF>.csv`. Phone evidence at 2026-08-07 19:10:26 UTC showed:

```text
M15 retained from 2026-07-31
H1  retained from 2026-07-10
H4  covered June-July
D1  covered June-July
```

Standalone M15 files covered only 2026-02-27 through 2026-03-06.

Therefore retained local inputs could not support a complete June-July replay. The production indicator builder also uses a safe window of 500 bars, so acquiring only from 2026-06-01 would under-warm early-June replay decisions.

The isolated collector writes only below:

```text
data/replay/<dataset-id>/
```

It never writes the production candle cache.

## PR #6 salvage decision

Draft PR #6 contained useful historical-replay design work but was not an integration source for current `main`.

It was closed as superseded after the canonical collector/reconciliation work. It remains historical design evidence only and must not be revived or merged wholesale.

Validated architectural ideas retained in the canonical implementation include explicit historical ranges, bounded chunking, raw evidence preservation, immutable output, checksums, path containment, and fail-closed validation.

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

## Canonical collector and verifier

```text
tools/fetch_historical_candles.py
tools/verify_replay_dataset.py
tests/test_fetch_historical_candles.py
tests/test_verify_replay_dataset.py
.github/workflows/historical-candle-acquisition.yml
```

Key merges:

```text
PR #57 canonical immutable collector
PR #59 reconciliation / single acquisition path
PR #60 provider-aligned leading candle handling
PR #61 transient transport retry handling
PR #62 reusable offline dataset verifier
```

Exact later merge identifiers:

```text
PR #60=8e746e554b1d754f9e427a80eab3cc694871dc08
PR #61=ce7d2bc097f2130f663193d49e5e97c62bcf2095
PR #62=be8ab1cc903f8c8b88c1c6fa7a358348f5786c1b
```

## Safety and integrity properties

The collector/verifier package provides:

- preview/no-network mode by default;
- network acquisition only with explicit `--execute`;
- explicit `from`/`to` requests with no `count` parameter;
- bounded requests below OANDA's 5000-candle limit;
- bounded HTTP response size and timeout;
- at most three HTTP attempts per chunk;
- retry for HTTP 429 and 5xx;
- retry for transient `OSError` / `http.client.HTTPException` transport failures;
- bounded backoff beginning at 0.5 seconds;
- response attempt preservation for HTTP responses;
- redacted immutable metadata preservation for transport-error attempts where no response body exists;
- raw provider JSON persisted before semantic validation;
- complete midpoint candles only;
- OHLC validity checks;
- one provider-aligned leading candle permitted only when its interval overlaps request `from`;
- older/multiple leading candles still rejected;
- post-window candles still rejected;
- exact duplicate boundary reconciliation and conflicting-duplicate rejection;
- final half-open requested range filtering;
- production-compatible five-column candle CSVs;
- immutable dataset IDs: an existing dataset is never overwritten;
- SHA-256 and byte-size records for persisted artifacts;
- `FAILED.json` preservation when acquisition fails after dataset creation;
- no Telegram, Supabase, order placement, strategy, service, cron, threshold, pair-list or production-cache mutation.

The reusable verifier independently checks manifest identity/scope, `FAILED.json` absence, artifact path containment, byte counts and SHA-256, canonical CSV structure, timestamp ordering/range, OHLC integrity, manifest-vs-CSV row/first/last agreement, pre-evaluation warm-up and non-empty evaluation coverage.

## Initial offline implementation validation

PR #57 focused validation originally passed 11 collector tests, with no real provider, Telegram or Supabase calls. Subsequent PRs added provider-alignment, transport-retry and verifier regression coverage. Exact final-head CI/static-analysis gates were required before each merge.

## Acquisition attempt 1 — fail-closed provider alignment edge

Recorded phone evidence: **2026-08-07 20:10:49 UTC**.

```text
dataset=data/replay/oanda-20260601-20260801-20260807/
COLLECTOR_EXECUTION=FAIL
FAILED_EVIDENCE_PRESERVED=YES
ERROR_TYPE=ValueError
ERROR=OANDA returned candle outside requested chunk for EURUSD H4: 2026-05-31T21:00:00Z
```

Classification: OANDA returned one H4 candle beginning before literal request `from` but overlapping that instant because of provider candle alignment. The collector originally rejected every earlier start.

Disposition: fixed by PR #60. Validation now permits at most one genuinely overlapping provider-aligned leading candle while retaining fail-closed behavior for older/multiple/trailing out-of-window data. The failed dataset remains immutable forensic evidence.

## Warm-up correction before attempt 2

`tools/build_indicators.py` uses:

```text
SAFE_WINDOW=500
validate_tf_window=200
min_bars=60
EMA9 EMA21 RSI14 MACD12/26/9 ADX14 ATR14 BB20
```

The selected reusable raw range was therefore expanded to:

```text
raw_range=[2024-01-01T00:00:00Z, 2026-08-01T00:00:00Z)
replay_evaluation=[2026-06-01T00:00:00Z, 2026-08-01T00:00:00Z)
```

No-network preview at **2026-08-07 20:25:37 UTC** passed:

```text
PREVIEW_STATUS=PASS
MODE=preview
NETWORK_PERMITTED=False
PRODUCTION_CACHE_TOUCHED=False
STREAM_COUNT=8
TOTAL_PLANNED_REQUESTS=60
```

## Acquisition attempt 2 — transient TLS failure

Recorded start: **2026-08-07 20:29:19 UTC**.

```text
dataset=data/replay/oanda-warmup-20240101-20260801-20260807-r2/
```

During execution, a read-only status check showed active progress:

```text
RAW_RESPONSES=45
METADATA_FILES=45
COMPLETED_STREAM_CSVS=4
LATEST_ARTIFACT_AGE_SEC=1
MATCHING_PROCESS_COUNT=1
```

Terminal result:

```text
COLLECTOR_EXECUTION=FAIL
FAILED_EVIDENCE_PRESERVED=YES
ERROR_TYPE=SSLEOFError
ERROR=[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1032)
PRODUCTION_CACHE_UNCHANGED=YES
ACQUISITION_STATUS=FAIL
```

Classification: transient transport resilience gap. The collector retried HTTP 429/5xx but did not retry a TLS/socket exception raised before an HTTP response existed.

Disposition: fixed by PR #61 using the same bounded maximum-three-attempt policy, with immutable transport-error metadata and a deterministic `SSLEOFError -> SSLEOFError -> 200` regression test. The failed r2 root remains immutable forensic evidence.

## Git SSH wrapper abort before successful attempt

A later orchestration wrapper unnecessarily required `git fetch origin main` before using already reviewed pinned code. The phone's Git SSH transport closed the connection on port 443:

```text
Connection closed by 151.124.191.231 port 443
fatal: Could not read from remote repository.
ACQUISITION_STATUS=ABORTED
REASON=GIT_FETCH_FAILED
```

This abort happened before OANDA acquisition and before r3 dataset creation. No strategy/runtime/provider mutation occurred.

The dependency was removed. The successful attempt instead downloaded exact immutable source files over ordinary HTTPS and proved their Git object identities before execution.

## Acquisition attempt 3 — successful immutable dataset

Canonical dataset:

```text
data/replay/oanda-warmup-20240101-20260801-20260807-r3/
```

Pinned-source proof:

```text
SOURCE_COMMIT=be8ab1cc903f8c8b88c1c6fa7a358348f5786c1b
COLLECTOR_EXPECTED_BLOB=e03e76ee3493b34e50ab88cd9df2ba30ce007f43
COLLECTOR_ACTUAL_BLOB=e03e76ee3493b34e50ab88cd9df2ba30ce007f43
VERIFIER_EXPECTED_BLOB=04dff84cbbd1a86a5508282f09b12726744778eb
VERIFIER_ACTUAL_BLOB=04dff84cbbd1a86a5508282f09b12726744778eb
SOURCE_INTEGRITY=PASS
```

Preview gate immediately before provider access:

```text
PREVIEW_MODE=preview
PREVIEW_NETWORK_PERMITTED=False
PREVIEW_STREAMS=8
PREVIEW_REQUESTS=60
PREVIEW_GATE=PASS
```

Final acquisition/verifier verdict:

```text
COLLECTOR_EXECUTION=PASS
VERIFIER_STATUS=PASS
MANIFEST_STATUS=COMPLETE
STREAM_COUNT=8
ARTIFACT_COUNT=128
ARTIFACT_HASH_FAILURES=0
OFFLINE_VERIFICATION=PASS
PRODUCTION_CACHE_UNCHANGED=YES
TRACKED_WORKTREE_UNCHANGED=YES
ACQUISITION_STATUS=PASS
REPLAY_DATASET_ELIGIBLE=YES
```

Per-stream coverage:

```text
EURUSD D1  rows=670   warmup=626   evaluation=44   requests=1  attempts=1
EURUSD H1  rows=16078 warmup=15001 evaluation=1077 requests=6  attempts=6
EURUSD H4  rows=4020  warmup=3751  evaluation=269  requests=2  attempts=2
EURUSD M15 rows=64309 warmup=60001 evaluation=4308 requests=21 attempts=21
GBPUSD D1  rows=670   warmup=626   evaluation=44   requests=1  attempts=1
GBPUSD H1  rows=16078 warmup=15001 evaluation=1077 requests=6  attempts=6
GBPUSD H4  rows=4020  warmup=3751  evaluation=269  requests=2  attempts=2
GBPUSD M15 rows=64306 warmup=59998 evaluation=4308 requests=21 attempts=21
```

`http_attempts == request_count` for all eight streams. Every successful r3 request completed on the first attempt; the newly added transport retry was not needed in the successful run.

## Dataset disposition

```text
oanda-20260601-20260801-20260807          = FAILED_FORENSIC_EVIDENCE
oanda-warmup-20240101-20260801-20260807-r2 = FAILED_FORENSIC_EVIDENCE
oanda-warmup-20240101-20260801-20260807-r3 = CANONICAL_REPLAY_INPUT
```

Do not delete or overwrite the failed roots. Do not reacquire June-July simply because the old rolling live cache is short; r3 closes that input gap.

## Production mutation status

```text
STRATEGY_CHANGED=NO
THRESHOLDS_CHANGED=NO
PAIR_UNIVERSE_CHANGED=NO
COOLDOWN_CHANGED=NO
LIVE_FETCHER_CHANGED=NO
PRODUCTION_CACHE_CHANGED=NO
SERVICE_OR_CRON_CHANGED=NO
TELEGRAM_CHANGED=NO
SUPABASE_CHANGED=NO
```

## Final acquisition verdict

```text
HISTORICAL_DATA_PHASE=CLOSED_PASS
CANONICAL_DATASET=oanda-warmup-20240101-20260801-20260807-r3
REPLAY_INPUT_INTEGRITY=PASS
REPLAY_INPUT_WARMUP=PASS
REPLAY_ELIGIBLE=YES
```

## Next step

Do not modify production scoring yet. Complete the deterministic production-rule replay harness in PR #64, then run that reviewed harness twice against r3 and require identical output hashes before using its June-July decisions for the fixed A/B/C strategy comparison.
