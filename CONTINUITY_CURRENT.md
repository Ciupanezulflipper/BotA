# BotA Current Continuity State

Last updated: **2026-08-07 21:44 UTC**

## Authoritative identifiers

```text
RECORDED_DATE=2026-08-07
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=73b2306b5843f3396823ce815e96051abf78cf50
GITHUB_MAIN=ce7d2bc097f2130f663193d49e5e97c62bcf2095
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_SERVICE_DAEMON_PIDFILE=31140
```

## Runtime and live scope

```text
manager_count=1
required_services_running=7/7
owned_services=6/7
orphan_service=crond
watcher=RUNNING
PAIRS=EURUSD GBPUSD
TIMEFRAMES=M15
FILTER_SCORE_MIN_ALL=65
H1_VETO_OVERRIDE_SCORE=75
TELEGRAM_MIN_SCORE=70
TELEGRAM_TIER_YELLOW_MIN=70
TELEGRAM_TIER_GREEN_MIN=75
TELEGRAM_COOLDOWN_SECONDS=1800
DRY_RUN_MODE=0
TELEGRAM_ENABLED=1
```

Runtime ownership remains degraded, but the watcher is producing decisions and Telegram transport is proven to work. Only two pairs are live.

## Proven signal funnel

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 410 rejected by H1-neutral veto
  -> 4 rejected by H4+D1 opposition
  -> 110 strategy-accepted
```

Retained accepted-to-Telegram outcomes:

```text
61 sent
38 cooldown-suppressed
6 Telegram score-gated
1 send failure
```

BotA can emit signals. The current investigation is signal quality/calibration, not basic Telegram transport.

## Outcome evidence

Supabase BotA M15 published outcomes on/after 2026-06-01:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
```

March local ledger joined 51/51 to score components:

```text
BASELINE: N=51 W=13 L=38 PIPS=-264.1
ADX<30: N=17 W=9 L=8 PIPS=+98.0
SCORE>=70 + ADX<30: N=12 W=9 L=3 PIPS=+174.2
```

Later June-July component cross-check recovered 9/13 published signals:

```text
MATCHED_BASELINE: N=9 W=2 L=7 PIPS=-70.2
SCORE>=70 + ADX<30: N=5 W=2 L=3 PIPS=+13.1
SCORE>=70 + ADX<30 + NO_EXTREME: N=4 W=2 L=2 PIPS=+28.9
ADX>=30 within matched sample: 0W / 4L / -83.3 pips
```

This supports replay-testing ADX calibration but is not production approval.

## Local retention and raw-input gaps

The four unmatched June 23-26 published outcomes cannot be reconstructed from retained `logs/alerts.csv`.

Verified live candle coverage at 2026-08-07 19:10:26 UTC for both pairs:

```text
M15: 499 rows, 2026-07-31 15:00 UTC -> 2026-08-07 19:30 UTC
H1 : 499 rows, 2026-07-10 00:00 UTC -> 2026-08-07 18:00 UTC
H4 : 499 rows, 2026-04-14 13:00 UTC -> 2026-08-07 13:00 UTC
D1 : 499 rows, 2024-09-02 21:00 UTC -> 2026-08-05 21:00 UTC
```

Standalone `data/EURUSD_M15.csv` and `data/GBPUSD_M15.csv` contain only 2026-02-27 through 2026-03-06. The live fetcher uses a rolling `count=500`, so it is not a complete replay source.

## Historical acquisition package

Canonical acquisition path:

```text
tools/fetch_historical_candles.py
tests/test_fetch_historical_candles.py
.github/workflows/historical-candle-acquisition.yml
```

Collector contract after PR #61:

```text
DEFAULT_MODE=PREVIEW_NO_NETWORK
EXECUTION_REQUIRES=--execute
OUTPUT_NAMESPACE=data/replay/<dataset-id>
OUTPUT_IMMUTABLE=YES
PRODUCTION_CACHE_TOUCHED=NO
OANDA_PRICE=M
PAIRS=EURUSD GBPUSD
TIMEFRAMES=M15 H1 H4 D1
RAW_RESPONSES_PRESERVED=YES
RETRYABLE_HTTP=429_AND_5XX
RETRYABLE_TRANSPORT=OSError_AND_HTTPException
MAX_HTTP_ATTEMPTS=3
RETRY_BACKOFF_SECONDS=0.5
MANIFEST_SHA256=YES
PROVIDER_ALIGNED_LEADING_CANDLE=ONE_OVERLAPPING_ALLOWED
```

PR #60 merged provider-aligned boundary handling at:

```text
8e746e554b1d754f9e427a80eab3cc694871dc08
```

PR #61 merged transient transport retry handling at:

```text
ce7d2bc097f2130f663193d49e5e97c62bcf2095
```

On PR #61 exact head: historical-acquisition CI passed, Security Scan passed, DeepSource Python/Shell/Secrets passed, Sonar passed with 0 new issues / 0 security hotspots, and no inline review threads were open. CodeRabbit remained non-blocking/pending at merge time.

## Historical dataset attempt 1 — boundary failure preserved

Recorded: **2026-08-07 20:10:49 UTC**.

```text
dataset=data/replay/oanda-20260601-20260801-20260807/
COLLECTOR_EXECUTION=FAIL
ERROR_TYPE=ValueError
ERROR=OANDA returned candle outside requested chunk for EURUSD H4: 2026-05-31T21:00:00Z
FAILED_EVIDENCE_PRESERVED=YES
```

Classification: provider-aligned H4 leading candle overlapped request start. Fixed by PR #60 without weakening other boundary checks.

## Replay warm-up requirement

`tools/build_indicators.py` uses:

```text
SAFE_WINDOW=500
validate_tf_window=200
min_bars=60
EMA9 EMA21 RSI14 MACD12/26/9 ADX14 ATR14 BB20
```

Therefore a replay dataset beginning exactly at 2026-06-01 is under-warmed for early-June decisions.

Selected acquisition/evaluation ranges:

```text
raw_range=[2024-01-01T00:00:00Z, 2026-08-01T00:00:00Z)
replay_evaluation=[2026-06-01T00:00:00Z, 2026-08-01T00:00:00Z)
```

No-network warm-up preview passed at **2026-08-07 20:25:37 UTC**:

```text
PREVIEW_STATUS=PASS
STREAM_COUNT=8
TOTAL_PLANNED_REQUESTS=60
NETWORK_PERMITTED=False
PRODUCTION_CACHE_TOUCHED=False
FAILED_DATASET_PRESERVED=YES
```

## Historical dataset attempt 2 — transient TLS failure preserved

Recorded start: **2026-08-07 20:29:19 UTC**.

```text
dataset=data/replay/oanda-warmup-20240101-20260801-20260807-r2/
```

Live progress at **2026-08-07 20:31:12 UTC**:

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

Classification: transient transport-resilience gap. Fixed by PR #61 with bounded retry and immutable transport-error metadata. Regression coverage proves `SSLEOFError -> SSLEOFError -> 200` recovery.

`GIT_WORKTREE_STATUS_UNCHANGED=NO` from that wrapper is not by itself evidence of tracked production mutation because the check included untracked replay artifacts. The production candle-cache SHA-256 remained identical. Future wrappers compare tracked diffs separately.

## Dataset disposition

Both failed datasets remain immutable forensic evidence and are not replay inputs:

```text
data/replay/oanda-20260601-20260801-20260807/
data/replay/oanda-warmup-20240101-20260801-20260807-r2/
```

The next acquisition must use a new dataset ID.

## Reusable replay dataset verifier — in review

Branch:

```text
feat/replay-dataset-verifier-20260807
```

New reusable offline verifier:

```text
tools/verify_replay_dataset.py
tests/test_verify_replay_dataset.py
```

It replaces the large disposable post-acquisition Termux verification block. It verifies manifest identity/scope, artifact SHA-256 and byte counts, path containment, canonical candle CSV structure, timestamp ordering/range, OHLC integrity, manifest-vs-CSV row/first/last agreement, `FAILED.json` absence, at least 500 pre-evaluation candles per stream, and non-empty evaluation coverage.

Audit:

```text
audits/REPLAY_DATASET_VERIFIER_2026-08-07.md
```

The historical-acquisition workflow is extended to compile and run both acquisition and verifier test suites.

## Efficiency operating model

Canonical workflow: `docs/FORENSIC_OPERATING_MODEL.md`.

```text
GitHub connector   -> code/history/docs/tests
Supabase connector -> published signal/outcome truth
Phone/Termux       -> runtime-only state, credentials, local-only evidence
```

Do not issue ad-hoc phone probes for information available through connectors. Reusable tools replace disposable shell/Python probes.

## Scope lock

Do not lower score/H1/Telegram floors, remove cooldown, add a third pair, or mutate ADX/RSI scoring yet.

Do not use `tools/backtest_bota.py` as production-rule validation because its strategy/scoring path differs from the live watcher.

Never push directly to `main`; use branch -> complete-file writes -> verified diff -> PR.

## Evidence

- `audits/REPLAY_DATASET_VERIFIER_2026-08-07.md`
- `audits/HISTORICAL_ACQUISITION_TRANSPORT_FAILURE_2026-08-07.md`
- `audits/HISTORICAL_ACQUISITION_RUNTIME_EDGE_2026-08-07.md`
- `audits/HISTORICAL_CANDLE_ACQUISITION_2026-08-07.md`
- `audits/HISTORICAL_ACQUISITION_RECONCILIATION_2026-08-07.md`
- `audits/RAW_CANDLE_REPLAY_GAP_2026-08-07.md`
- `docs/FORENSIC_OPERATING_MODEL.md`
- `audits/LOCAL_RETENTION_GAP_2026-08-07.md`
- `audits/JUNE_JULY_ADX_RSI_TEMPORAL_CROSSCHECK_2026-08-07.md`
- `audits/ADX_RSI_COUNTERFACTUAL_2026-08-07.md`
- `audits/MARCH_COMPONENT_OUTCOMES_2026-08-07.md`
- `audits/COOLDOWN_AND_SIGNAL_QUALITY_2026-08-07.md`
- `audits/SIGNAL_DELIVERY_FUNNEL_2026-08-07.md`
- `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`
- `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`

## Exactly one next action

Complete review/CI for the reusable dataset verifier. If all material gates pass, merge it and run one new immutable warm-up acquisition using a new dataset ID, then verify it with the reviewed verifier from the same commit.

After dataset integrity passes, build/run the deterministic production-semantics replay:

```text
A = current production baseline
B = score >=70 AND ADX <30
C = score >=70 AND ADX <30 AND no extreme RSI
```

No production strategy mutation before that replay.
