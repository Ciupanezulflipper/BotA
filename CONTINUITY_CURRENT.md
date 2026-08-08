# BotA Current Continuity State

Last updated: **2026-08-07 23:46 UTC**

## Authoritative identifiers

```text
RECORDED_DATE=2026-08-07
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=73b2306b5843f3396823ce815e96051abf78cf50
GITHUB_MAIN_AT_PHASE2_RUNNER_MERGE=91f81ddf28e6b0fadfa2e87a3f71f9464c962073
PHASE1_PR=64
PHASE1_FINAL_HEAD=ff77b2cc05b4c0bffe0ac13893ae6431264e08d8
PHASE1_MERGE=6b437179cc58021aa358b1d0b04c121d9304c660
PHASE2_RUNNER_PR=66
PHASE2_RUNNER_FINAL_HEAD=a3193eacb5450c143a459acb456037ab3833962c
PHASE2_RUNNER_MERGE=91f81ddf28e6b0fadfa2e87a3f71f9464c962073
PHASE2_RUNNER_BLOB=bed536931026231956536543b914703e7ee096d2
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_SERVICE_DAEMON_PIDFILE=31140
```

## Current investigation state

```text
HISTORICAL_DATA_PHASE=CLOSED_PASS
DETERMINISTIC_REPLAY_HARNESS_PHASE=CLOSED_PASS
FULL_JUNE_JULY_REPLAY_EXECUTION_PHASE=CLOSED_PASS
OUTCOME_MATCH_AND_ABC_COMPARISON_PHASE=NEXT
ROBUSTNESS_FINAL_VERDICT_PHASE=PENDING
PRODUCTION_STRATEGY_MUTATION_ALLOWED=NO
```

BotA can emit signals. The current investigation is signal quality/calibration, not basic Telegram transport, historical-data availability, or replay determinism.

## Runtime and live scope

Latest verified effective settings remain:

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

## Proven historical signal funnel

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

## Published outcome evidence motivating calibration work

Supabase BotA M15 outcomes in `[2026-06-01, 2026-08-01)` were re-queried after the deterministic replay pass and remain:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
```

The exact 13 rows are the database truth to be frozen for the next matching phase. Supabase `created_at` must **not** be used as the sole replay identity key because publication time can differ from watcher decision time.

Earlier evidence:

```text
MARCH_BASELINE: N=51 W=13 L=38 PIPS=-264.1
MARCH_ADX_LT30: N=17 W=9 L=8 PIPS=+98.0
MARCH_SCORE70_ADX_LT30: N=12 W=9 L=3 PIPS=+174.2
MARCH_SCORE70_ADX_LT30_NO_EXTREME: N=7 W=7 L=0 PIPS=+171.0

JUNE_JULY_OLD_MATCHED_BASELINE: N=9 W=2 L=7 PIPS=-70.2
JUNE_JULY_OLD_SCORE70_ADX_LT30: N=5 W=2 L=3 PIPS=+13.1
JUNE_JULY_OLD_SCORE70_ADX_LT30_NO_EXTREME: N=4 W=2 L=2 PIPS=+28.9
JUNE_JULY_OLD_ADX_GTE30: 0W / 4L / -83.3 pips
OLD_MATCH_RATE=69.2%
```

The March 7/7 subgroup remains explicitly overfit-risk. The older 9/13 June-July component match is superseded as a completeness target by the deterministic event ledger but remains historical evidence.

## Frozen candidate policies

These were fixed before observing the full June-July replay counts:

```text
A = current production acceptance
B = A AND score >=70 AND ADX <30
C = B AND no extreme RSI

SELL extreme RSI <=30
BUY  extreme RSI >=70
```

Do not move these thresholds after seeing replay results and then describe the result as the original test.

## Historical-data phase — CLOSED PASS

Canonical successful replay input:

```text
DATASET_ID=oanda-warmup-20240101-20260801-20260807-r3
RAW_RANGE=[2024-01-01T00:00:00Z,2026-08-01T00:00:00Z)
EVALUATION_RANGE=[2026-06-01T00:00:00Z,2026-08-01T00:00:00Z)
REPLAY_DATASET_ELIGIBLE=YES
DATASET_MANIFEST_SHA256=e0033c797fc561935beebd27eaa275c0c659ccaac93acfaa2309abf8354ecf2f
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

Two earlier failed immutable roots remain forensic evidence and must not be deleted or reused:

```text
data/replay/oanda-20260601-20260801-20260807/
data/replay/oanda-warmup-20240101-20260801-20260807-r2/
```

Do not reacquire another June-July dataset unless r3 itself is proven corrupt.

## Deterministic replay harness — Phase 1 CLOSED PASS

PR #64 introduced the reviewed deterministic replay implementation:

```text
tools/replay_semantics.py
tools/deterministic_replay.py
tests/test_deterministic_replay.py
audits/DETERMINISTIC_REPLAY_HARNESS_2026-08-07.md
audits/DETERMINISTIC_REPLAY_PHASE1_PROOF_2026-08-07.md
```

Immutable Phase-1 provenance:

```text
PR=64
FINAL_PR_HEAD=ff77b2cc05b4c0bffe0ac13893ae6431264e08d8
MERGE_COMMIT=6b437179cc58021aa358b1d0b04c121d9304c660
```

Replay grade:

```text
DETERMINISTIC_PRODUCTION_RULES_WITH_PROVIDER_SUBSTITUTION
```

The harness uses completed candles only, reconstructs historical UTC market-hours/session semantics, reuses production indicator/quality/SR math, reproduces the current 1.0 ATR pullback buffer and ADX<20 behavior, reproduces H1/H4/D1 fusion semantics, and performs no live-provider/Telegram/Supabase/service/cron/cooldown/production-cache mutation.

Exact historical `emit_snapshot.py` network responses were not retained; verified OANDA H4/D1 bundles are used with the same vote formula and the provider substitution is explicit. Historical D1 runtime-cache values are not established in tracked evidence, so the baseline replay preserves production fail-open `ANY` semantics.

## Deterministic full execution — Phase 2 CLOSED PASS

PR #66 added the reusable reviewed execution wrapper:

```text
tools/run_phase2_determinism.sh
```

Final PR #66 exact-head gates:

```text
FINAL_HEAD=a3193eacb5450c143a459acb456037ab3833962c
HISTORICAL_AND_REPLAY_CI=PASS
CI_RUN_NUMBER=46
SECURITY_SCAN=PASS
SECURITY_RUN_NUMBER=1085
DEEPSOURCE_PYTHON=PASS
DEEPSOURCE_SHELL=PASS
DEEPSOURCE_SECRETS=PASS
SONAR_QUALITY_GATE=PASS
SONAR_NEW_ISSUES=0
SONAR_SECURITY_HOTSPOTS=0
CODERABBIT_FINAL_STATUS=SUCCESS_RATE_LIMITED
MERGE_COMMIT=91f81ddf28e6b0fadfa2e87a3f71f9464c962073
```

CodeRabbit's final status was rate-limited and is not treated as substantive final review evidence. Earlier substantive CodeRabbit findings on failure exit semantics, dependency verification, signal handling, and atomic/exclusive publication were incorporated before the final clean head.

The phone downloaded the merged runner and verified its exact blob before execution:

```text
RUNNER_EXPECTED_BLOB=bed536931026231956536543b914703e7ee096d2
RUNNER_ACTUAL_BLOB=bed536931026231956536543b914703e7ee096d2
RUNNER_INTEGRITY=PASS
DEVICE_UTC=2026-08-07 23:46:14 UTC
```

Every downloaded replay dependency matched its reviewed Git blob ID and:

```text
REPLAY_SOURCE_INTEGRITY=PASS
PRODUCTION_SOURCE_BLOBS_MATCH=YES
```

The full June-July replay was executed twice:

```text
RUN1_RC=0
RUN2_RC=0
RUN1_EVENTS_SHA256=05089e6d97e4ab9f3a522d9ec1188c24e69637bf048f1cd1403f23772ec8dabc
RUN2_EVENTS_SHA256=05089e6d97e4ab9f3a522d9ec1188c24e69637bf048f1cd1403f23772ec8dabc
EVENT_BYTES_IDENTICAL=YES
RUN1_SUMMARY_SHA256=f00e42962dd08f7aef7f5e2ecb5d3475d57bbca8abc3bce9f4d2d0d70b903594
RUN2_SUMMARY_SHA256=f00e42962dd08f7aef7f5e2ecb5d3475d57bbca8abc3bce9f4d2d0d70b903594
SUMMARY_BYTES_IDENTICAL=YES
PHASE2_DETERMINISM_GATE=PASS
```

Canonical local result:

```text
CANONICAL_REPLAY_RESULT=data/replay_results/phase2-june-july-pr64
REPLAY_STATUS=COMPLETE
REPLAY_GRADE=DETERMINISTIC_PRODUCTION_RULES_WITH_PROVIDER_SUBSTITUTION
DECISION_ROWS=8618
```

Frozen-policy acceptance counts:

```text
POLICY_A_ACCEPTED=105
POLICY_B_ACCEPTED=51
POLICY_C_ACCEPTED=45
```

Replay funnel:

```text
ACCEPTED=105
H1_CONFIRM=461
H4_D1_CONFIRM=10
M15_SETUP_OR_SCORE=4104
MARKET_CLOSED=3938
TOTAL=8618
```

These are reconstruction counts only. They do not establish trade profitability.

Isolation proof:

```text
PRODUCTION_CACHE_SHA256_BEFORE=8d407d175e23929dd3ff2c898ee994670ca1057a2dfdfd0c3c61acc91fbb0847
PRODUCTION_CACHE_SHA256_AFTER=8d407d175e23929dd3ff2c898ee994670ca1057a2dfdfd0c3c61acc91fbb0847
PRODUCTION_CACHE_UNCHANGED=YES
TRACKED_WORKTREE_UNCHANGED=YES
PRODUCTION_STRATEGY_MUTATION=NO
TELEGRAM_MUTATION=NO
SUPABASE_MUTATION=NO
SERVICE_CRON_MUTATION=NO
```

Detailed proof:

```text
audits/DETERMINISTIC_REPLAY_PHASE2_EXECUTION_2026-08-07.md
```

## New live-code finding preserved by replay

Current `m15_h1_fusion.sh` reads top-level:

```text
.adx // 0
```

for the H1-opposite override. Current `scoring_engine.sh` does not emit a top-level `adx` field. Therefore the intended `ADX>=40` opposite-trend override receives `0` and cannot activate as written under the inspected production contract.

Replay reproduces this behavior. Production is **not** changed yet.

## Scope lock

Until outcome matching plus robustness/holdout evidence completes:

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
Phone/Termux       -> runtime-only state, credentials, local-only immutable data/results
```

Do not re-probe facts already captured in canonical audits. Reusable reviewed tools replace disposable shell/Python probes.

## Key evidence

- `audits/DETERMINISTIC_REPLAY_PHASE2_EXECUTION_2026-08-07.md`
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

## Exactly one next action — outcome matching and frozen A/B/C comparison

Build and review one reusable tool that consumes the canonical local deterministic event ledger:

```text
data/replay_results/phase2-june-july-pr64/events.jsonl
```

and a frozen snapshot of the 13 Supabase M15 outcomes in the evaluation interval.

Matching contract must:

```text
PAIR_MATCH=REQUIRED
DIRECTION_MATCH=REQUIRED
ENTRY_PRICE_CONSISTENCY=REQUIRED
BOUNDED_TEMPORAL_CONSISTENCY=REQUIRED
CREATED_AT_AS_SOLE_KEY=FORBIDDEN
AMBIGUOUS_MATCH=REPORT_NOT_FORCE
ONE_REPLAY_EVENT_PER_PUBLISHED_SIGNAL=REQUIRED
```

Only after the matching gate is explicit/reproducible may observed outcome statistics be calculated for frozen policies A/B/C.

No production strategy mutation before that comparison and the robustness/final-verdict phase.
