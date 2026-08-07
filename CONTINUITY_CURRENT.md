# BotA Current Continuity State

Last updated: **2026-08-07 23:05 UTC**

## Authoritative identifiers

```text
RECORDED_DATE=2026-08-07
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=73b2306b5843f3396823ce815e96051abf78cf50
GITHUB_MAIN_BASE=22a6238c40a6dbbb65c15c42b908c5df5753a288
REPLAY_BRANCH=feat/deterministic-production-replay-20260807
REPLAY_PR=64
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
H1_TREND_MIN_SCORE=40
H1_VETO_OVERRIDE_SCORE=75
H1_VETO_OVERRIDE_ADX=40
TELEGRAM_MIN_SCORE=70
TELEGRAM_TIER_YELLOW_MIN=70
TELEGRAM_TIER_GREEN_MIN=75
TELEGRAM_COOLDOWN_SECONDS=1800
DRY_RUN_MODE=0
TELEGRAM_ENABLED=1
```

Runtime ownership remains degraded, but the watcher is producing decisions and Telegram transport is proven to work. Only two pairs are live. Runtime ownership is not the current signal-quality bottleneck.

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

BotA can emit signals. The investigation is signal quality/calibration, not basic Telegram transport.

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

These observations justify testing ADX/RSI calibration. They are not production approval.

## Local retention gap — closed by immutable acquisition

The four unmatched June 23-26 published outcomes could not be reconstructed from retained `logs/alerts.csv`.

Verified rolling live candle coverage on 2026-08-07 19:10:26 UTC for both pairs was insufficient for a full June-July replay:

```text
M15: 499 rows, 2026-07-31 15:00 UTC -> 2026-08-07 19:30 UTC
H1 : 499 rows, 2026-07-10 00:00 UTC -> 2026-08-07 18:00 UTC
H4 : 499 rows, 2026-04-14 13:00 UTC -> 2026-08-07 13:00 UTC
D1 : 499 rows, 2024-09-02 21:00 UTC -> 2026-08-05 21:00 UTC
```

Standalone M15 files contain only 2026-02-27 through 2026-03-06. This local-retention limitation is now superseded for replay purposes by the verified immutable r3 dataset below.

## Historical acquisition package

Canonical acquisition/verifier paths:

```text
tools/fetch_historical_candles.py
tools/verify_replay_dataset.py
tests/test_fetch_historical_candles.py
tests/test_verify_replay_dataset.py
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

Key merges:

```text
PR #60 alignment fix: 8e746e554b1d754f9e427a80eab3cc694871dc08
PR #61 transport retry: ce7d2bc097f2130f663193d49e5e97c62bcf2095
PR #62 replay verifier: be8ab1cc903f8c8b88c1c6fa7a358348f5786c1b
```

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

A raw dataset beginning exactly on 2026-06-01 would therefore be under-warmed for early-June decisions.

Selected raw/evaluation ranges:

```text
raw_range=[2024-01-01T00:00:00Z, 2026-08-01T00:00:00Z)
replay_evaluation=[2026-06-01T00:00:00Z, 2026-08-01T00:00:00Z)
```

No-network warm-up preview passed at **2026-08-07 20:25:37 UTC** with 8 streams and 60 planned requests.

## Historical dataset attempt 2 — transient TLS failure preserved

Recorded start: **2026-08-07 20:29:19 UTC**.

```text
dataset=data/replay/oanda-warmup-20240101-20260801-20260807-r2/
COLLECTOR_EXECUTION=FAIL
FAILED_EVIDENCE_PRESERVED=YES
ERROR_TYPE=SSLEOFError
ERROR=[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1032)
PRODUCTION_CACHE_UNCHANGED=YES
ACQUISITION_STATUS=FAIL
```

Classification: transient transport-resilience gap. Fixed by PR #61 with bounded retry and immutable transport-error metadata.

The earlier wrapper printed `GIT_WORKTREE_STATUS_UNCHANGED=NO` because it compared untracked replay artifacts as well as tracked files; the production candle-cache SHA-256 remained identical. Later wrappers corrected this by comparing tracked diffs separately.

## Historical dataset attempt 3 — PASS / replay eligible

Pinned-source acquisition used exact PR #62 merge code over HTTPS after a non-mutating phone Git SSH fetch attempt was aborted by a transient `Connection closed ... port 443` error.

Pinned source proof:

```text
SOURCE_COMMIT=be8ab1cc903f8c8b88c1c6fa7a358348f5786c1b
COLLECTOR_EXPECTED_BLOB=e03e76ee3493b34e50ab88cd9df2ba30ce007f43
COLLECTOR_ACTUAL_BLOB=e03e76ee3493b34e50ab88cd9df2ba30ce007f43
VERIFIER_EXPECTED_BLOB=04dff84cbbd1a86a5508282f09b12726744778eb
VERIFIER_ACTUAL_BLOB=04dff84cbbd1a86a5508282f09b12726744778eb
SOURCE_INTEGRITY=PASS
```

Dataset:

```text
data/replay/oanda-warmup-20240101-20260801-20260807-r3/
```

Final acquisition/integrity verdict:

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

Verified stream coverage:

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

Every successful r3 provider request completed on its first HTTP attempt. Historical-data acquisition/integrity is now **closed**; do not reacquire another dataset for this June-July replay unless r3 itself is later proven corrupt.

## Failed dataset disposition

Both failed roots remain immutable forensic evidence and are not replay inputs:

```text
data/replay/oanda-20260601-20260801-20260807/
data/replay/oanda-warmup-20240101-20260801-20260807-r2/
```

The successful r3 root is the canonical replay input.

## Deterministic production-rule replay — Phase 1 in progress

PR #64:

```text
branch=feat/deterministic-production-replay-20260807
base=22a6238c40a6dbbb65c15c42b908c5df5753a288
```

Harness paths:

```text
tools/replay_semantics.py
tools/deterministic_replay.py
tests/test_deterministic_replay.py
audits/DETERMINISTIC_REPLAY_HARNESS_2026-08-07.md
```

The harness is read-only with respect to production state. It uses completed candles only, reuses production Python indicator/quality/SR math, reconstructs historical market/session semantics, and freezes candidate policies before observing full June-July replay outcomes:

```text
A = current production acceptance
B = A AND score >=70 AND ADX <30
C = B AND no extreme RSI
```

Extreme RSI remains frozen as:

```text
SELL extreme: RSI <=30
BUY extreme: RSI >=70
```

Replay grade is intentionally declared as:

```text
DETERMINISTIC_PRODUCTION_RULES_WITH_PROVIDER_SUBSTITUTION
```

because historical `emit_snapshot.py` H4/D1 provider responses from TwelveData/Yahoo cannot be recreated byte-for-byte. The exact vote formula is applied to the verified historical OANDA H4/D1 bundles instead.

The historical writer/values for runtime `cache/d1_trend_<PAIR>.json` are not established in tracked evidence. Baseline replay therefore uses the scoring engine's fail-open `ANY` behavior; EMA is available only as a separate sensitivity mode.

## New Phase-1 code finding — H1 opposite override cannot use raw ADX as written

Current `m15_h1_fusion.sh` consumes:

```text
.adx // 0
```

for its H1-opposite override, while current `scoring_engine.sh` does not emit a top-level `adx` field. It embeds ADX in reasons; later observability fields expose raw ADX, but the JSON field read by this override is absent.

Under the inspected production contract, this particular override therefore receives `0` and cannot activate via the intended `ADX>=40` condition. The replay deliberately reproduces that behavior. No production fix is included in Phase 1.

## PR #64 proof status

On intermediate head `d83700d84f8be666a6a3a050d7c9f682c830bf91`:

```text
HISTORICAL_ACQUISITION_AND_REPLAY_CI=PASS
SECURITY_SCAN=PASS
DEEPSOURCE_SHELL=PASS
DEEPSOURCE_SECRETS=PASS
DEEPSOURCE_PYTHON=FAIL
SONAR_QUALITY_GATE=PASS_BUT_10_NEW_MAINTAINABILITY_ISSUES
```

The branch was **not merged** at that state. The Python findings were complexity/style findings in replay-only code, not production mutations. Refactoring is in progress and all final gate claims must be made only against the exact later PR head.

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

- `audits/DETERMINISTIC_REPLAY_HARNESS_2026-08-07.md`
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

Finish PR #64 refactoring and require the exact final head to pass replay/acquisition CI, Security Scan, DeepSource Python/Shell/Secrets, and Sonar with zero new material issues before merge.

After Phase 1 merges, run the deterministic harness **twice** against r3 and require identical event SHA-256 output before using the replay for the Phase-2 A/B/C outcome comparison.

No production strategy mutation before Phase 2 and robustness validation.
