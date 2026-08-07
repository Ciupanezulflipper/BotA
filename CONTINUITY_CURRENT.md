# BotA Current Continuity State

Last updated: **2026-08-07 23:26 UTC**

## Authoritative identifiers

```text
RECORDED_DATE=2026-08-07
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=73b2306b5843f3396823ce815e96051abf78cf50
GITHUB_MAIN=6b437179cc58021aa358b1d0b04c121d9304c660
PHASE1_PR=64
PHASE1_FINAL_HEAD=ff77b2cc05b4c0bffe0ac13893ae6431264e08d8
PHASE1_MERGE=6b437179cc58021aa358b1d0b04c121d9304c660
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_SERVICE_DAEMON_PIDFILE=31140
```

## Current investigation state

```text
HISTORICAL_DATA_PHASE=CLOSED_PASS
DETERMINISTIC_REPLAY_HARNESS_PHASE=CLOSED_PASS
FULL_JUNE_JULY_REPLAY_PHASE=NEXT
ROBUSTNESS_FINAL_VERDICT_PHASE=PENDING
PRODUCTION_STRATEGY_MUTATION_ALLOWED=NO
```

BotA can emit signals. The current investigation is signal quality/calibration, not basic Telegram transport or historical-data availability.

## Runtime and live scope

Latest verified effective settings:

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

Runtime ownership remains degraded, but it is not the current signal-quality bottleneck. Only two pairs are live.

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

Cooldown audit showed all 38 retained cooldown blocks were non-exact updates; this does not prove they were independent trades and does not justify removing cooldown wholesale.

## Outcome evidence motivating replay

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
SCORE>=70 + ADX<30 + NO_EXTREME: N=7 W=7 L=0 PIPS=+171.0
```

The 7/7 March subgroup is explicitly treated as overfit-risk, not as a 100%-win strategy claim.

Later June-July component cross-check recovered 9/13 published signals:

```text
MATCHED_BASELINE: N=9 W=2 L=7 PIPS=-70.2
SCORE>=70 + ADX<30: N=5 W=2 L=3 PIPS=+13.1
SCORE>=70 + ADX<30 + NO_EXTREME: N=4 W=2 L=2 PIPS=+28.9
ADX>=30 within matched sample: 0W / 4L / -83.3 pips
MATCH_RATE=69.2%
```

This is enough to justify replay-testing ADX/RSI calibration but not enough for production approval.

## Frozen candidate policies

These were fixed before observing full June-July replay results:

```text
A = current production acceptance
B = A AND score >=70 AND ADX <30
C = B AND no extreme RSI

SELL extreme RSI <=30
BUY  extreme RSI >=70
```

Do not move these thresholds after seeing replay results and then describe the result as the original test.

## Historical-data phase — closed PASS

Retained rolling live data was insufficient for full June-July replay. The immutable acquisition package was built and verified through PRs #57, #59, #60, #61 and #62.

Relevant later merge identifiers:

```text
PR #60 provider-aligned leading candle fix=8e746e554b1d754f9e427a80eab3cc694871dc08
PR #61 transient transport retry fix=ce7d2bc097f2130f663193d49e5e97c62bcf2095
PR #62 reusable replay dataset verifier=be8ab1cc903f8c8b88c1c6fa7a358348f5786c1b
```

Two failed immutable roots remain forensic evidence:

```text
data/replay/oanda-20260601-20260801-20260807/
data/replay/oanda-warmup-20240101-20260801-20260807-r2/
```

Canonical successful replay input:

```text
DATASET_ID=oanda-warmup-20240101-20260801-20260807-r3
RAW_RANGE=[2024-01-01T00:00:00Z,2026-08-01T00:00:00Z)
EVALUATION_RANGE=[2026-06-01T00:00:00Z,2026-08-01T00:00:00Z)
REPLAY_DATASET_ELIGIBLE=YES
```

Pinned acquisition-source proof:

```text
SOURCE_COMMIT=be8ab1cc903f8c8b88c1c6fa7a358348f5786c1b
COLLECTOR_EXPECTED_BLOB=e03e76ee3493b34e50ab88cd9df2ba30ce007f43
COLLECTOR_ACTUAL_BLOB=e03e76ee3493b34e50ab88cd9df2ba30ce007f43
VERIFIER_EXPECTED_BLOB=04dff84cbbd1a86a5508282f09b12726744778eb
VERIFIER_ACTUAL_BLOB=04dff84cbbd1a86a5508282f09b12726744778eb
SOURCE_INTEGRITY=PASS
```

Final r3 integrity verdict:

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

All r3 provider requests completed on their first HTTP attempt. Do not reacquire another June-July dataset unless r3 itself is later proven corrupt.

## Deterministic replay harness — Phase 1 closed PASS

PR #64 introduced:

```text
tools/replay_semantics.py
tools/deterministic_replay.py
tests/test_deterministic_replay.py
audits/DETERMINISTIC_REPLAY_HARNESS_2026-08-07.md
```

Final immutable proof:

```text
PR=64
FINAL_PR_HEAD=ff77b2cc05b4c0bffe0ac13893ae6431264e08d8
MERGE_COMMIT=6b437179cc58021aa358b1d0b04c121d9304c660
MAIN_AFTER_MERGE=6b437179cc58021aa358b1d0b04c121d9304c660
CHANGED_FILES=7
BEHIND_MAIN_BEFORE_MERGE=0
```

Exact final-head gates:

```text
HISTORICAL_AND_REPLAY_CI=PASS
CI_RUN_NUMBER=39
CI_RUN_ID=31226834369

SECURITY_SCAN=PASS
SECURITY_RUN_NUMBER=1065
SECURITY_RUN_ID=31226834370

DEEPSOURCE_PYTHON=PASS
DEEPSOURCE_SHELL=PASS
DEEPSOURCE_SECRETS=PASS
CODERABBIT=SUCCESS

SONAR_CHECK_ID=93022819471
SONAR_QUALITY_GATE=PASS
SONAR_NEW_ISSUES=0
SONAR_SECURITY_HOTSPOTS=0
```

All final review threads were resolved before merge. The merge was executed with `expected_head_sha=ff77b2cc05b4c0bffe0ac13893ae6431264e08d8`.

Detailed immutable proof:

```text
audits/DETERMINISTIC_REPLAY_PHASE1_PROOF_2026-08-07.md
```

## Replay fidelity contract

Replay grade:

```text
DETERMINISTIC_PRODUCTION_RULES_WITH_PROVIDER_SUBSTITUTION
```

The harness:

- uses completed candles only; no future H1/H4/D1 candle is exposed to an earlier M15 decision;
- reuses production `build_indicators.py`, `quality_filter.py` and `sr_score.py` math;
- reconstructs historical UTC market-hours and session-score semantics;
- reproduces current 1.0 ATR pullback buffer;
- reproduces ADX<20 hard HOLD and current scoring components;
- preserves the production ADX-block numeric `volatility=0.0` quirk;
- reproduces H1 neutral/opposite logic and H4+D1 veto structure;
- performs no provider, Telegram, Supabase, service, cron, cooldown, production-cache or strategy mutation.

Exact historical `emit_snapshot.py` TwelveData/Yahoo responses were not retained. Replay therefore applies the same vote formula to verified OANDA H4/D1 bundles and declares that provider substitution explicitly.

Historical `cache/d1_trend_<PAIR>.json` values/writer are not established in tracked evidence. Baseline replay uses the scoring engine's fail-open `ANY`; EMA is sensitivity-only.

## Pinned production-source provenance

Replay verifies these source Git object IDs before executing:

```text
tools/scoring_engine.sh      09c42362a5c3c679696e86d4131ce5dfabd86608
tools/m15_h1_fusion.sh       c1de0312ed928f870b9a45df109b730d30888ee7
tools/quality_filter.py       18b76f908652d483c115c930373972836cea81dc
tools/build_indicators.py     2abce4a325d6d9da8bb0958b97a651d4288e1792
tools/sr_score.py             616b996a8ce439a19483762645a2247ca96fd066
tools/market_open.sh          a73ca97f3a63c3245311585e231e5e69eaffc506
tools/emit_snapshot.py        425c9adace57956981cf7e3111fd5df504c4f1ca
```

`tools/deterministic_replay.py` resolves Git to an absolute executable and uses `git hash-object --no-filters` to compare the actual source files against this map before replay. It also re-runs the canonical dataset verifier and records SHA-256 of the exact r3 `manifest.json` bytes.

## New live-code finding from Phase 1

Current `m15_h1_fusion.sh` reads top-level:

```text
.adx // 0
```

for the H1-opposite override. Current `scoring_engine.sh` does not emit a top-level `adx` field. Therefore the intended `ADX>=40` opposite-trend override receives `0` and cannot activate as written under the inspected production contract.

Replay reproduces this behavior. Production is **not** changed yet.

## Scope lock

Until replay + robustness evidence completes:

```text
DO_NOT_LOWER_SCORE_FLOOR=YES
DO_NOT_LOWER_H1_FLOOR=YES
DO_NOT_CHANGE_TELEGRAM_FLOORS=YES
DO_NOT_REMOVE_COOLDOWN=YES
DO_NOT_ADD_THIRD_PAIR=YES
DO_NOT_MUTATE_ADX_RULE=YES
DO_NOT_MUTATE_RSI_RULE=YES
DO_NOT_FIX_H1_ADX_OVERRIDE_IN_PRODUCTION_YET=YES
```

`tools/backtest_bota.py` remains unsuitable as production-rule validation because its strategy/scoring path differs from the live watcher.

## Efficiency operating model

Canonical workflow: `docs/FORENSIC_OPERATING_MODEL.md`.

```text
GitHub connector   -> code/history/docs/tests
Supabase connector -> published signal/outcome truth
Phone/Termux       -> runtime-only state, credentials, local-only evidence
```

Do not re-probe facts already captured in canonical audits. Reusable tools replace disposable shell/Python probes.

## Key evidence

- `audits/DETERMINISTIC_REPLAY_PHASE1_PROOF_2026-08-07.md`
- `audits/DETERMINISTIC_REPLAY_HARNESS_2026-08-07.md`
- `audits/HISTORICAL_CANDLE_ACQUISITION_2026-08-07.md`
- `audits/REPLAY_DATASET_VERIFIER_2026-08-07.md`
- `audits/HISTORICAL_ACQUISITION_TRANSPORT_FAILURE_2026-08-07.md`
- `audits/HISTORICAL_ACQUISITION_RUNTIME_EDGE_2026-08-07.md`
- `audits/HISTORICAL_ACQUISITION_RECONCILIATION_2026-08-07.md`
- `audits/RAW_CANDLE_REPLAY_GAP_2026-08-07.md`
- `audits/LOCAL_RETENTION_GAP_2026-08-07.md`
- `audits/JUNE_JULY_ADX_RSI_TEMPORAL_CROSSCHECK_2026-08-07.md`
- `audits/ADX_RSI_COUNTERFACTUAL_2026-08-07.md`
- `audits/MARCH_COMPONENT_OUTCOMES_2026-08-07.md`
- `docs/FORENSIC_OPERATING_MODEL.md`

## Exactly one next action — Phase 2 deterministic execution gate

Run the exact merged replay harness **twice** against canonical r3 for the frozen June-July interval and require identical event bytes before interpreting strategy performance:

```text
RUN1_EVENTS_SHA256 == RUN2_EVENTS_SHA256
RUN1_SUMMARY_CORE == RUN2_SUMMARY_CORE
EXPECTED_PRODUCTION_SOURCE_BLOBS == OBSERVED_PRODUCTION_SOURCE_BLOBS
DATASET_MANIFEST_SHA256_PRESENT=YES
PRODUCTION_CACHE_UNCHANGED=YES
TRACKED_WORKTREE_UNCHANGED=YES
```

If determinism passes, compare replay reconstruction to known published signal evidence and evaluate A/B/C outcomes. That is Phase 2.

No production strategy mutation before Phase 2 and the robustness/final-verdict phase.
