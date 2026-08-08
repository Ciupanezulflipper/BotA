# BotA AI Start Here

Last updated: **2026-08-08 01:37 UTC**

Read this before proposing BotA commands, code, service, strategy, Telegram, provider, Supabase, replay, or deployment changes.

## Current authoritative truth

```text
RECORDED_DATE=2026-08-08
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=73b2306b5843f3396823ce815e96051abf78cf50
LIVE_WATCHER=RUNNING
LIVE_PAIRS=EURUSD_GBPUSD_ONLY
LIVE_TIMEFRAME=M15
FILTER_SCORE_MIN_ALL=65
H1_VETO_OVERRIDE_SCORE=75
TELEGRAM_MIN_SCORE=70
TELEGRAM_COOLDOWN_SECONDS=1800
DRY_RUN_MODE=0
TELEGRAM_ENABLED=1
HISTORICAL_DATA_PHASE=CLOSED_PASS
DETERMINISTIC_REPLAY_HARNESS_PHASE=CLOSED_PASS
FULL_JUNE_JULY_REPLAY_EXECUTION=CLOSED_PASS
PUBLISHED_OUTCOME_MATCH_GATE=FAIL_9_OF_13
MATCH_GAP_CLASSIFICATION=CLOSED_PASS
ROBUSTNESS_FINAL_VERDICT=NEXT
PRODUCTION_STRATEGY_MUTATION_ALLOWED=NO
```

## Read first

1. `CONTINUITY_CURRENT.md` — current state and exactly one next action.
2. `audits/REPLAY_OUTCOME_MATCH_GAP_RESULT_2026-08-08.md` — executed Phase 2.3 result.
3. `audits/REPLAY_OUTCOME_MATCH_GAP_CLASSIFICATION_2026-08-08.md` — reviewed classifier contract and one-to-one integrity fix.
4. `audits/REPLAY_OUTCOME_MATCHER_2026-08-07.md` — frozen matching contract defined before the result.
5. `audits/DETERMINISTIC_REPLAY_PHASE2_EXECUTION_2026-08-07.md` — canonical deterministic replay proof.
6. `docs/FORENSIC_OPERATING_MODEL.md` — mandatory connector-first workflow.

Older dated audits remain evidence. Do not restart closed acquisition/runtime branches without new contradictory evidence.

## Current diagnosis

BotA can emit BUY/SELL decisions and Telegram can send them. The investigation is signal quality/calibration, not basic transport, historical-data availability, or replay determinism.

Published BotA M15 outcomes in the frozen June-July database window remain:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
```

The full deterministic replay produced:

```text
DECISION_ROWS=8618
POLICY_A_ACCEPTED=105
POLICY_B_ACCEPTED=51
POLICY_C_ACCEPTED=45
```

Frozen policies were selected before observing these replay results:

```text
A = current production acceptance
B = A AND score >=70 AND ADX <30
C = B AND no extreme RSI
SELL extreme RSI <=30
BUY  extreme RSI >=70
```

## Canonical historical dataset and replay

```text
DATASET_ID=oanda-warmup-20240101-20260801-20260807-r3
REPLAY_DATASET_ELIGIBLE=YES
DATASET_MANIFEST_SHA256=e0033c797fc561935beebd27eaa275c0c659ccaac93acfaa2309abf8354ecf2f
CANONICAL_REPLAY_RESULT=data/replay_results/phase2-june-july-pr64
EVENTS_SHA256=05089e6d97e4ab9f3a522d9ec1188c24e69637bf048f1cd1403f23772ec8dabc
SUMMARY_SHA256=f00e42962dd08f7aef7f5e2ecb5d3475d57bbca8abc3bce9f4d2d0d70b903594
PHASE2_DETERMINISM_GATE=PASS
EVENT_BYTES_IDENTICAL=YES
SUMMARY_BYTES_IDENTICAL=YES
PRODUCTION_SOURCE_BLOBS_MATCH=YES
PRODUCTION_CACHE_UNCHANGED=YES
TRACKED_WORKTREE_UNCHANGED=YES
REPLAY_GRADE=DETERMINISTIC_PRODUCTION_RULES_WITH_PROVIDER_SUBSTITUTION
```

Do not reacquire the historical interval or rerun deterministic replay unless the canonical evidence itself is proven invalid.

## Published-outcome matching — Phase 2.2

PR #68 merged the reviewed offline matcher and frozen Supabase fixture:

```text
PR68_FINAL_HEAD=49ff1d2341cb9157acafb223950e79cb66883a1a
PR68_MERGE=bfa7f69ef430000994ea06aa7a3ba713a4144d90
MATCHER_BLOB=a5453fa6d17b447eb87072e2f2685453e2d4d067
FIXTURE_BLOB=8f321dddb645130d9be01a22f8ba14e8f2f81501
```

Frozen match contract:

```text
POLICY_A_CURRENT=TRUE
PAIR=EXACT
DIRECTION=EXACT
ENTRY_DIFF<=5.0_PIPS
ABS(PUBLISHED_CREATED_AT-REPLAY_DECISION_TIME)<=45_MINUTES
CREATED_AT_AS_SOLE_KEY=FORBIDDEN
AMBIGUOUS_MATCH=REPORT_NOT_FORCE
ONE_TO_ONE_ASSIGNMENT=REQUIRED
```

Canonical local comparison:

```text
COMPARISON_SHA256=6abb46288522b615e904ad67bc8e173786e1fddf560563b516e653b5b97f2274
MATCH_GATE=FAIL
MATCHED_OUTCOMES=9
UNMATCHED_OUTCOMES=4
AMBIGUOUS_OUTCOMES=0
MATCH_RATE_PERCENT=69.23
```

Observed published-outcome subsets among the nine uniquely reconstructed outcomes:

```text
A: N=9 W=3 L=6 C=0 PIPS=-23.50
B: N=5 W=3 L=2 C=0 PIPS=+54.50
C: N=5 W=3 L=2 C=0 PIPS=+54.50
```

Policy B remains promising in the reconstructed sample. Policy C adds no incremental benefit over B in that sample. These are not full replay PnL results and do not authorize production changes.

## Match-gap classification — Phase 2.3 CLOSED PASS

PR #69 merged the reviewed diagnostic classifier after fixing a real one-to-one assignment edge case discovered during review:

```text
PR69_FINAL_HEAD=440def4e9781ba60a55c625046ca0795e536987d
PR69_MERGE=cbd0c3126ecac7b3b03e060eb81c144711b786f2
CLASSIFIER_BLOB=126ab302e246d8e4a9e254ccf77c80f92bd2b979
```

Canonical local execution:

```text
GAP_CLASSIFIER_STATUS=COMPLETE
UNMATCHED_COUNT=4
CONSUMED_MATCHED_EVENTS=9
CLASSIFIER_RC=0
GAP_RESULT_JSON=VALID
GAP_RESULT_SHA256=5cbf0537a5bc3800e3a3353843d440d04a8e98b10287b81a525a106bf2aae471
TOLERANCE_WIDENED=NO
NETWORK_USED=NO
PRODUCTION_MUTATION=NO
```

Exact classifications:

```text
01f33b41-68cf-4975-a0d9-8ef4699c1d54 EURUSD SELL
LIVE_PUBLISHED_BUT_REPLAY_NOT_ACCEPTED_WITHIN_45M
same_dir_45=4 accepted_45=0 published=0.00 CANCELLED

0a95433f-6dbe-48c3-b6f3-e43fe996c8f9 EURUSD SELL
LIVE_PUBLISHED_BUT_REPLAY_NOT_ACCEPTED_WITHIN_45M
same_dir_45=1 accepted_45=0 published=-15.80

78a0ad15-b53b-4eb3-ad8d-453bc7d667f1 EURUSD SELL
REPLAY_ACCEPTED_WITHIN_45M_BUT_ENTRY_DIFF_GT_5P
same_dir_45=3 accepted_45=1 published=-13.50

ed386a21-1431-4b05-9941-2017789297bb GBPUSD SELL
LIVE_PUBLISHED_BUT_REPLAY_NOT_ACCEPTED_WITHIN_45M
same_dir_45=4 accepted_45=0 published=-18.60
```

Therefore all four match gaps are now classified:

```text
UNEXPLAINED_GAP_COUNT=0
LIVE_VS_REPLAY_DECISION_STATE_DIVERGENCES=3
LIVE_VS_REPLAY_ENTRY_DIVERGENCES=1
MATCHER_BUG_AS_EXPLANATION=NOT_SUPPORTED
TOLERANCE_WIDENING_NEEDED=NO
```

The three decision divergences are not hypothetical Policy-B/C trades because B and C are subsets of reconstructed Policy A. The one entry-divergent accepted replay event still needs its detailed score/ADX/RSI/policy flags from the already-preserved Phase 2.3 JSON before the robustness verdict.

## Important production-code finding preserved by replay

Current `m15_h1_fusion.sh` reads top-level `.adx // 0` for the H1-opposite override, while current scoring JSON does not emit a top-level `adx` field. Therefore the intended `ADX>=40` opposite-trend override receives zero and cannot activate under the inspected production contract.

Replay reproduces this behavior. Do not fix production yet; robustness evidence comes first.

## Mandatory source hierarchy

```text
GitHub connector   -> code, commits, PRs, docs, tests
Supabase connector -> published signal/outcome/database truth
Phone/Termux       -> runtime-only state, credentials, local-only immutable data/results
```

Do not ask for ad-hoc phone probes for facts already obtainable through connectors. Reusable reviewed tools are preferred when local-only evidence must be consumed.

## Scope lock

Until robustness/holdout evidence completes:

```text
DO_NOT_WIDEN_MATCH_TOLERANCES=YES
DO_NOT_RERUN_HISTORICAL_ACQUISITION=YES
DO_NOT_RERUN_DETERMINISTIC_REPLAY=YES
DO_NOT_RERUN_CANONICAL_OUTCOME_MATCHER=YES
DO_NOT_RERUN_GAP_CLASSIFIER=YES
DO_NOT_LOWER_SCORE_FLOOR=YES
DO_NOT_LOWER_H1_FLOOR=YES
DO_NOT_CHANGE_TELEGRAM_FLOORS=YES
DO_NOT_REMOVE_COOLDOWN=YES
DO_NOT_ADD_THIRD_PAIR=YES
DO_NOT_MUTATE_ADX_RULE=YES
DO_NOT_MUTATE_RSI_RULE=YES
DO_NOT_FIX_H1_ADX_OVERRIDE_IN_PRODUCTION_YET=YES
```

Do not use `tools/backtest_bota.py` as production-rule validation because its strategy semantics differ from the live watcher.

Never push directly to `main`. Use branch -> complete-file writes -> verified diff -> PR -> exact-head gates -> merge.

## Exactly one next action

Read the already-preserved canonical Phase 2.3 result once:

```text
data/replay_results/phase2-june-july-pr64/match_gap_classification.json
GAP_RESULT_SHA256=5cbf0537a5bc3800e3a3353843d440d04a8e98b10287b81a525a106bf2aae471
```

Extract only the detailed replay state needed for the robustness verdict: reject stage/filter reasons/H1-H4-D1 state for the three decision divergences, and score/ADX/RSI/entry/time deltas plus Policy B/C flags for the one entry-divergent accepted event.

This is a local read only. Do not rerun acquisition, replay, the canonical outcome matcher, or the gap classifier. No production strategy mutation yet.
