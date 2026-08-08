# BotA Current Continuity State

Last updated: **2026-08-08 01:31 UTC**

## Authoritative identifiers

```text
RECORDED_DATE=2026-08-08
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=73b2306b5843f3396823ce815e96051abf78cf50
PHASE1_REPLAY_PR=64
PHASE1_REPLAY_MERGE=6b437179cc58021aa358b1d0b04c121d9304c660
PHASE2_RUNNER_PR=66
PHASE2_RUNNER_MERGE=91f81ddf28e6b0fadfa2e87a3f71f9464c962073
PHASE2_DOCS_PR=67
PHASE2_DOCS_MERGE=c6637b2e13ee856f84f2bfa7706ba84becbb9c5f
OUTCOME_MATCHER_PR=68
OUTCOME_MATCHER_FINAL_HEAD=49ff1d2341cb9157acafb223950e79cb66883a1a
OUTCOME_MATCHER_MERGE=bfa7f69ef430000994ea06aa7a3ba713a4144d90
OUTCOME_MATCHER_BLOB=a5453fa6d17b447eb87072e2f2685453e2d4d067
OUTCOME_FIXTURE_BLOB=8f321dddb645130d9be01a22f8ba14e8f2f81501
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_SERVICE_DAEMON_PIDFILE=31140
```

## Current investigation state

```text
HISTORICAL_DATA_PHASE=CLOSED_PASS
DETERMINISTIC_REPLAY_HARNESS_PHASE=CLOSED_PASS
FULL_JUNE_JULY_REPLAY_EXECUTION_PHASE=CLOSED_PASS
PUBLISHED_OUTCOME_MATCH_GATE=FAIL_9_OF_13
MATCH_GAP_CLASSIFICATION_PHASE=NEXT
ROBUSTNESS_FINAL_VERDICT_PHASE=PENDING
PRODUCTION_STRATEGY_MUTATION_ALLOWED=NO
```

BotA can emit signals. The current investigation is signal quality/calibration, not Telegram transport, historical-data availability, or replay determinism.

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

Runtime ownership remains degraded but is not the current signal-quality bottleneck. Only two pairs are live.

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

Cooldown audit showed all 38 retained cooldown blocks were non-exact updates; this does not prove independent trades and does not justify removing cooldown wholesale.

## Frozen candidate policies

Selected before the full June-July replay result was observed:

```text
A = current production acceptance
B = A AND score >=70 AND ADX <30
C = B AND no extreme RSI
SELL extreme RSI <=30
BUY  extreme RSI >=70
```

Do not move these thresholds after seeing replay results and describe the result as the original test.

## Historical-data phase — CLOSED PASS

Canonical replay input:

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
```

Two earlier failed immutable roots remain forensic evidence and must not be deleted/reused:

```text
data/replay/oanda-20260601-20260801-20260807/
data/replay/oanda-warmup-20240101-20260801-20260807-r2/
```

Do not reacquire June-July unless r3 itself is proven corrupt.

## Deterministic replay — CLOSED PASS

Reviewed replay source merge:

```text
PR64_FINAL_HEAD=ff77b2cc05b4c0bffe0ac13893ae6431264e08d8
PR64_MERGE=6b437179cc58021aa358b1d0b04c121d9304c660
REPLAY_GRADE=DETERMINISTIC_PRODUCTION_RULES_WITH_PROVIDER_SUBSTITUTION
```

PR #66 added the reviewed deterministic double-run wrapper. The phone verified its exact merged blob and every replay dependency before execution.

Canonical execution proof:

```text
DEVICE_UTC=2026-08-07 23:46:14 UTC
RUN1_RC=0
RUN2_RC=0
RUN1_EVENTS_SHA256=05089e6d97e4ab9f3a522d9ec1188c24e69637bf048f1cd1403f23772ec8dabc
RUN2_EVENTS_SHA256=05089e6d97e4ab9f3a522d9ec1188c24e69637bf048f1cd1403f23772ec8dabc
EVENT_BYTES_IDENTICAL=YES
RUN1_SUMMARY_SHA256=f00e42962dd08f7aef7f5e2ecb5d3475d57bbca8abc3bce9f4d2d0d70b903594
RUN2_SUMMARY_SHA256=f00e42962dd08f7aef7f5e2ecb5d3475d57bbca8abc3bce9f4d2d0d70b903594
SUMMARY_BYTES_IDENTICAL=YES
PRODUCTION_SOURCE_BLOBS_MATCH=YES
PRODUCTION_CACHE_UNCHANGED=YES
TRACKED_WORKTREE_UNCHANGED=YES
PHASE2_DETERMINISM_GATE=PASS
```

Canonical local replay result:

```text
CANONICAL_REPLAY_RESULT=data/replay_results/phase2-june-july-pr64
DECISION_ROWS=8618
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

Known fidelity limits remain explicit: historical live `emit_snapshot.py` provider responses were not retained, so replay uses verified OANDA H4/D1 bundles with the same vote formula; historical D1 runtime-cache values are not established, so baseline preserves production fail-open `ANY` semantics.

## Published outcome truth

Supabase BotA M15 outcomes in `[2026-06-01,2026-08-01)` were re-queried and remain:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
```

Supabase `created_at` is publication time and must never be the sole replay identity key.

## Published-outcome matcher — PR #68 CLOSED PASS

PR #68 added:

```text
tools/compare_replay_outcomes.py
tests/test_compare_replay_outcomes.py
audits/fixtures/supabase_bota_m15_20260601_20260801.json
audits/REPLAY_OUTCOME_MATCHER_2026-08-07.md
```

Final exact-head proof:

```text
FINAL_HEAD=49ff1d2341cb9157acafb223950e79cb66883a1a
OFFLINE_REPLAY_TESTS=PASS
SECURITY_SCAN=PASS
DEEPSOURCE_PYTHON=PASS
DEEPSOURCE_SHELL=PASS
DEEPSOURCE_SECRETS=PASS
SONAR_QUALITY_GATE=PASS
SONAR_NEW_ISSUES=0
SONAR_SECURITY_HOTSPOTS=0
CODERABBIT_STATUS=SUCCESS_RATE_LIMITED_NOT_REVIEW_EVIDENCE
MERGE_COMMIT=bfa7f69ef430000994ea06aa7a3ba713a4144d90
```

The matching contract was frozen before the canonical result:

```text
POLICY_A_CURRENT=TRUE
PAIR=EXACT
DIRECTION=EXACT
ENTRY_ABSOLUTE_DIFFERENCE<=5.0_PIPS
ABS(PUBLISHED_CREATED_AT-REPLAY_DECISION_TIME)<=45_MINUTES
CREATED_AT_AS_SOLE_KEY=FORBIDDEN
AMBIGUOUS_MATCH=REPORT_NOT_FORCE
ONE_TO_ONE_ASSIGNMENT=REQUIRED
```

## Canonical Phase-2.2 matching result — PARTIAL

Phone verified the merged matcher and fixture blobs, executed offline, and preserved:

```text
CANONICAL_COMPARISON_RESULT=data/replay_results/phase2-june-july-pr64/outcome_comparison.json
COMPARISON_SHA256=6abb46288522b615e904ad67bc8e173786e1fddf560563b516e653b5b97f2274
MATCHER_SOURCE_INTEGRITY=PASS
MATCHER_RC=0
COMPARISON_JSON=VALID
NETWORK_USED=NO
PRODUCTION_MUTATION=NO
```

Result:

```text
MATCH_GATE=FAIL
MATCH_STATUS=PARTIAL_MATCH
PUBLISHED_OUTCOMES=13
MATCHED_OUTCOMES=9
UNMATCHED_OUTCOMES=4
AMBIGUOUS_OUTCOMES=0
MATCH_RATE_PERCENT=69.23
```

Observed published-outcome subsets among the nine uniquely reconstructed trades:

```text
A: N=9 W=3 L=6 C=0 PIPS=-23.50
B: N=5 W=3 L=2 C=0 PIPS=+54.50
C: N=5 W=3 L=2 C=0 PIPS=+54.50
```

Interpretation:

- B remains materially better than A in the reconstructable subset.
- C provides no incremental benefit over B in this subset because the same five matched outcomes pass B and C.
- These are observed published-outcome counterfactuals, not full replay PnL.
- Production strategy mutation remains forbidden until the four missing live trades are classified and robustness/full outcome resolution completes.

The four unmatched published outcomes are:

```text
78a0ad15-b53b-4eb3-ad8d-453bc7d667f1  EURUSD SELL score80 CLOSED    -13.50
ed386a21-1431-4b05-9941-2017789297bb  GBPUSD SELL score75 CLOSED    -18.60
0a95433f-6dbe-48c3-b6f3-e43fe996c8f9  EURUSD SELL score85 CLOSED    -15.80
01f33b41-68cf-4975-a0d9-8ef4699c1d54  EURUSD SELL score75 CANCELLED   0.00
```

Combined unmatched outcome:

```text
N=4
WINS=0
LOSSES=3
CANCELLED=1
PIPS=-47.90
```

Reconciliation:

```text
MATCHED_PIPS=-23.50
UNMATCHED_PIPS=-47.90
ALL_13_PUBLISHED_PIPS=-71.40
```

Do not credit the unmatched losses to Policy B/C until replay state around each publication is classified.

## New live-code finding preserved by replay

Current `m15_h1_fusion.sh` reads top-level `.adx // 0` for the H1-opposite override. Current `scoring_engine.sh` does not emit a top-level `adx` field. The intended `ADX>=40` opposite-trend override therefore receives zero and cannot activate under the inspected production contract.

Replay reproduces this behavior. Production remains unchanged.

## Gap-classifier branch contract

The current branch adds:

```text
tools/classify_replay_match_gaps.py
tests/test_classify_replay_match_gaps.py
audits/REPLAY_OUTCOME_MATCH_GAP_CLASSIFICATION_2026-08-08.md
```

It does **not** rematch or widen tolerances. It enforces the canonical event and comparison SHA-256 values and requires the original 45-minute / 5-pip contract to still be present in the comparison JSON.

For each of the four gaps it reports exact same-direction replay state within the frozen 45-minute window and a separate bounded 180-minute near-miss diagnostic window. The 180-minute window is explicitly not a matching tolerance.

Primary classifications:

```text
NO_SAME_DIRECTION_EVENT_WITHIN_45M
LIVE_PUBLISHED_BUT_REPLAY_NOT_ACCEPTED_WITHIN_45M
REPLAY_ACCEPTED_WITHIN_45M_BUT_ENTRY_DIFF_GT_5P
```

### One-to-one consumed-event integrity

The canonical comparison already assigned nine replay events to its nine successful published-outcome matches. A gap scan must not treat those already-consumed events as available candidates for any of the four unmatched outcomes.

The reviewed classifier therefore reconstructs the nine consumed ledger indices from the immutable comparison `matched` rows and requires:

```text
CANONICAL_MATCHED_ROWS_REQUIRED=9
MATCHED_EVENT_IDENTITY=(pair,decision_time)
MATCHED_EVENT_PAYLOAD_EQUALITY=REQUIRED
MATCHED_EVENT_IDENTITIES_UNIQUE=REQUIRED
CONSUMED_MATCHED_EVENT_COUNT=9
CONSUMED_MATCHED_EVENTS_EXCLUDED_FROM_ALL_GAP_SCANS=YES
CANONICAL_COMPARISON_REWRITTEN=NO
CANONICAL_COMPARISON_RERUN=NO
```

Missing, duplicate, or payload-mismatched matched events fail closed. The consumed indices are removed before the frozen 45-minute candidate check, the 5-pip exact-candidate check, and the separate 180-minute diagnostic scan. A regression test covers the collision case where a consumed exact event must not produce a false matcher inconsistency.

If an unconsumed Policy-A event satisfying the original match contract is still found after those exclusions, the classifier fails closed as a genuine matcher inconsistency.

## Scope lock

Until match-gap classification plus robustness/holdout evidence completes:

```text
DO_NOT_WIDEN_MATCH_TOLERANCES=YES
DO_NOT_LOWER_SCORE_FLOOR=YES
DO_NOT_LOWER_H1_FLOOR=YES
DO_NOT_CHANGE_TELEGRAM_FLOORS=YES
DO_NOT_REMOVE_COOLDOWN=YES
DO_NOT_ADD_THIRD_PAIR=YES
DO_NOT_MUTATE_ADX_RULE=YES
DO_NOT_MUTATE_RSI_RULE=YES
DO_NOT_FIX_H1_ADX_OVERRIDE_IN_PRODUCTION_YET=YES
```

`tools/backtest_bota.py` remains unsuitable as production-rule validation because its semantics differ from the live watcher.

## Efficiency operating model

Canonical workflow: `docs/FORENSIC_OPERATING_MODEL.md`.

```text
GitHub connector   -> code/history/docs/tests
Supabase connector -> published signal/outcome/database truth
Phone/Termux       -> runtime-only state, credentials, local-only immutable data/results
```

Reusable reviewed tools replace disposable probes. Do not re-probe facts already captured in canonical audits.

## Key evidence

- `audits/REPLAY_OUTCOME_MATCH_GAP_CLASSIFICATION_2026-08-08.md`
- `audits/REPLAY_OUTCOME_MATCHER_2026-08-07.md`
- `audits/DETERMINISTIC_REPLAY_PHASE2_EXECUTION_2026-08-07.md`
- `audits/DETERMINISTIC_REPLAY_PHASE1_PROOF_2026-08-07.md`
- `audits/DETERMINISTIC_REPLAY_HARNESS_2026-08-07.md`
- `audits/HISTORICAL_CANDLE_ACQUISITION_2026-08-07.md`
- `audits/REPLAY_DATASET_VERIFIER_2026-08-07.md`
- `audits/JUNE_JULY_ADX_RSI_TEMPORAL_CROSSCHECK_2026-08-07.md`
- `audits/ADX_RSI_COUNTERFACTUAL_2026-08-07.md`
- `audits/MARCH_COMPONENT_OUTCOMES_2026-08-07.md`
- `docs/FORENSIC_OPERATING_MODEL.md`

## Exactly one next action — classify the four match gaps

Finish review and merge of the gap classifier, then run it once against:

```text
data/replay_results/phase2-june-july-pr64/events.jsonl
data/replay_results/phase2-june-july-pr64/outcome_comparison.json
audits/fixtures/supabase_bota_m15_20260601_20260801.json
```

Enforce:

```text
EVENTS_SHA256=05089e6d97e4ab9f3a522d9ec1188c24e69637bf048f1cd1403f23772ec8dabc
COMPARISON_SHA256=6abb46288522b615e904ad67bc8e173786e1fddf560563b516e653b5b97f2274
MATCH_TOLERANCE_WIDENED=NO
CONSUMED_MATCHED_EVENTS_EXCLUDED=YES
```

Use the resulting replay-state evidence to classify each missing live trade before any strategy change or robustness verdict. Do not rerun historical acquisition, deterministic replay, or the canonical outcome matcher.
