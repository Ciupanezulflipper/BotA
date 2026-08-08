# BotA Replay Outcome Match Gap Result

Recorded date: **2026-08-08 UTC**

## Purpose

Preserve the executed Phase 2.3 result from the reviewed gap classifier without rerunning historical acquisition, deterministic replay, or the canonical outcome matcher, and without widening the frozen matching contract.

## Provenance

```text
PR69_FINAL_HEAD=440def4e9781ba60a55c625046ca0795e536987d
PR69_MERGE=cbd0c3126ecac7b3b03e060eb81c144711b786f2
CLASSIFIER_BLOB=126ab302e246d8e4a9e254ccf77c80f92bd2b979
FIXTURE_BLOB=8f321dddb645130d9be01a22f8ba14e8f2f81501
EVENTS_SHA256=05089e6d97e4ab9f3a522d9ec1188c24e69637bf048f1cd1403f23772ec8dabc
COMPARISON_SHA256=6abb46288522b615e904ad67bc8e173786e1fddf560563b516e653b5b97f2274
```

The phone verified the merged classifier and frozen fixture blobs before execution.

## Execution verdict

```text
SOURCE_INTEGRITY=PASS
GAP_CLASSIFIER_STATUS=COMPLETE
UNMATCHED_COUNT=4
CONSUMED_MATCHED_EVENTS=9
CLASSIFIER_RC=0
GAP_RESULT_JSON=VALID
CANONICAL_GAP_RESULT=data/replay_results/phase2-june-july-pr64/match_gap_classification.json
GAP_RESULT_SHA256=5cbf0537a5bc3800e3a3353843d440d04a8e98b10287b81a525a106bf2aae471
TOLERANCE_WIDENED=NO
NETWORK_USED=NO
PRODUCTION_MUTATION=NO
```

The nine replay events already consumed by the nine successful canonical matches were excluded from every gap scan, preserving the one-to-one assignment semantics reviewed in PR #69.

## Exact four classifications

```text
01f33b41-68cf-4975-a0d9-8ef4699c1d54
EURUSD SELL
LIVE_PUBLISHED_BUT_REPLAY_NOT_ACCEPTED_WITHIN_45M
same_direction_within_45m=4
policy_a_accepted_within_45m=0
published_status=CANCELLED
published_result_pips=0.00

0a95433f-6dbe-48c3-b6f3-e43fe996c8f9
EURUSD SELL
LIVE_PUBLISHED_BUT_REPLAY_NOT_ACCEPTED_WITHIN_45M
same_direction_within_45m=1
policy_a_accepted_within_45m=0
published_status=CLOSED
published_result_pips=-15.80

78a0ad15-b53b-4eb3-ad8d-453bc7d667f1
EURUSD SELL
REPLAY_ACCEPTED_WITHIN_45M_BUT_ENTRY_DIFF_GT_5P
same_direction_within_45m=3
policy_a_accepted_within_45m=1
published_status=CLOSED
published_result_pips=-13.50

ed386a21-1431-4b05-9941-2017789297bb
GBPUSD SELL
LIVE_PUBLISHED_BUT_REPLAY_NOT_ACCEPTED_WITHIN_45M
same_direction_within_45m=4
policy_a_accepted_within_45m=0
published_status=CLOSED
published_result_pips=-18.60
```

## Interpretation

The four unmatched published outcomes are no longer unexplained retention gaps.

Three outcomes have same-pair/same-direction replay activity inside the original 45-minute window but no replay Policy-A acceptance. These are **live-vs-replay decision-state divergences**. They cannot be converted into matched trades by changing the timestamp tolerance, and they must not be credited to Policy B or C because B and C are subsets of replay Policy A.

The fourth outcome has one replay Policy-A acceptance inside 45 minutes but its replay entry differs from the published entry by more than the pre-frozen 5-pip limit. This is a **price/input reconstruction divergence**, not an absence of replay acceptance.

The result is consistent with the replay grade `DETERMINISTIC_PRODUCTION_RULES_WITH_PROVIDER_SUBSTITUTION`: the harness is deterministic for its frozen inputs, but it is not proven to recreate every unretained live provider/cache state exactly.

## What this does and does not prove

It proves:

```text
MATCHER_BUG_AS_EXPLANATION=NOT_SUPPORTED
ARBITRARY_TOLERANCE_WIDENING_NEEDED=NO
UNEXPLAINED_GAP_COUNT=0
LIVE_VS_REPLAY_DECISION_STATE_DIVERGENCES=3
LIVE_VS_REPLAY_ENTRY_DIVERGENCES=1
```

It does **not** prove that Policy B should be deployed. The matched published subset remains:

```text
A: N=9 W=3 L=6 C=0 PIPS=-23.50
B: N=5 W=3 L=2 C=0 PIPS=+54.50
C: N=5 W=3 L=2 C=0 PIPS=+54.50
```

Three of the four unmatched real outcomes are rejected under reconstructed Policy A, so they cannot be assigned hypothetical B/C outcomes from replay. The remaining entry-divergent accepted replay event still requires its exact score/ADX/RSI state to be read from the already-preserved Phase 2.3 JSON before the robustness verdict.

## Scope lock

```text
DO_NOT_WIDEN_MATCH_TOLERANCES=YES
DO_NOT_RERUN_HISTORICAL_ACQUISITION=YES
DO_NOT_RERUN_DETERMINISTIC_REPLAY=YES
DO_NOT_RERUN_CANONICAL_OUTCOME_MATCHER=YES
DO_NOT_MUTATE_ADX_RULE=YES
DO_NOT_MUTATE_RSI_RULE=YES
DO_NOT_LOWER_SCORE_FLOOR=YES
DO_NOT_LOWER_H1_FLOOR=YES
DO_NOT_CHANGE_TELEGRAM_FLOORS=YES
DO_NOT_REMOVE_COOLDOWN=YES
DO_NOT_ADD_THIRD_PAIR=YES
DO_NOT_FIX_H1_ADX_OVERRIDE_IN_PRODUCTION_YET=YES
PRODUCTION_STRATEGY_MUTATION_ALLOWED=NO
```

## Exactly one next action

Read the already-preserved canonical Phase 2.3 JSON once and extract the detailed replay state for the four gaps: reject stage/filter reasons/H1-H4-D1 state for the three decision divergences, and score/ADX/RSI/entry/time deltas plus Policy B/C flags for the one entry-divergent accepted event.

This is a local read only. Do not rerun any acquisition, replay, matcher, or classifier.
