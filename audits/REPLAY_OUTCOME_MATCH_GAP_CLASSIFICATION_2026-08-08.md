# BotA Replay Outcome Match Gap Classification

Recorded date: **2026-08-08 UTC**

## Purpose

Preserve the exact Phase-2.2 published-outcome matching result and define the next diagnostic gate without widening the pre-frozen match contract or mutating production strategy.

## Canonical inputs

Deterministic replay event ledger:

```text
data/replay_results/phase2-june-july-pr64/events.jsonl
EVENTS_SHA256=05089e6d97e4ab9f3a522d9ec1188c24e69637bf048f1cd1403f23772ec8dabc
REPLAY_EVENTS=8618
POLICY_A_REPLAY_ACCEPTED=105
POLICY_B_REPLAY_ACCEPTED=51
POLICY_C_REPLAY_ACCEPTED=45
```

Frozen published-outcome snapshot:

```text
audits/fixtures/supabase_bota_m15_20260601_20260801.json
PUBLISHED_OUTCOMES=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
```

Canonical local comparison:

```text
data/replay_results/phase2-june-july-pr64/outcome_comparison.json
COMPARISON_SHA256=6abb46288522b615e904ad67bc8e173786e1fddf560563b516e653b5b97f2274
```

## Frozen matching contract

The contract was documented before the canonical local result was observed:

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

These tolerances are not changed in this phase.

## Canonical Phase-2.2 result

Phone execution returned:

```text
MATCHER_SOURCE_INTEGRITY=PASS
MATCHER_RC=0
MATCH_GATE=FAIL
MATCH_STATUS=PARTIAL_MATCH
PUBLISHED_OUTCOMES=13
MATCHED_OUTCOMES=9
UNMATCHED_OUTCOMES=4
AMBIGUOUS_OUTCOMES=0
MATCH_RATE_PERCENT=69.23
COMPARISON_JSON=VALID
NETWORK_USED=NO
PRODUCTION_MUTATION=NO
```

Observed published-outcome subsets for the nine uniquely reconstructed trades:

```text
A: N=9 W=3 L=6 C=0 PIPS=-23.50
B: N=5 W=3 L=2 C=0 PIPS=+54.50
C: N=5 W=3 L=2 C=0 PIPS=+54.50
```

Interpretation is deliberately limited:

- Policy B remains materially better than A in the reconstructed subset.
- Policy C adds no incremental benefit over B in this subset because the same five matched outcomes pass B and C.
- These are **not** full replay PnL statistics. Only published outcomes have outcome truth here.
- Strategy mutation remains forbidden because four real published outcomes are still unreconstructed.

## Four unmatched published outcomes

The canonical comparison preserved these IDs. They were re-queried directly from Supabase after the local match result:

```text
78a0ad15-b53b-4eb3-ad8d-453bc7d667f1
EURUSD SELL
created_at=2026-06-09 16:01:36.90693+00
live_score=80
status=CLOSED
result_pips=-13.50

ed386a21-1431-4b05-9941-2017789297bb
GBPUSD SELL
created_at=2026-06-09 16:31:50.402806+00
live_score=75
status=CLOSED
result_pips=-18.60

0a95433f-6dbe-48c3-b6f3-e43fe996c8f9
EURUSD SELL
created_at=2026-06-17 18:31:29.124213+00
live_score=85
status=CLOSED
result_pips=-15.80

01f33b41-68cf-4975-a0d9-8ef4699c1d54
EURUSD SELL
created_at=2026-06-26 17:01:55.95831+00
live_score=75
status=CANCELLED
result_pips=0.00
```

Combined unmatched result:

```text
N=4
WINS=0
LOSSES=3
CANCELLED=1
TOTAL_PIPS=-47.90
```

This exactly reconciles the published total:

```text
MATCHED_PIPS=-23.50
UNMATCHED_PIPS=-47.90
ALL_13_PUBLISHED_PIPS=-71.40
```

The fact that the unreconstructed group is loss-heavy is important but cannot be credited to Policy B or C until replay-state diagnostics show whether those live trades would have failed the frozen policy filters.

## Gap-classifier contract

PR work in this branch adds:

```text
tools/classify_replay_match_gaps.py
tests/test_classify_replay_match_gaps.py
```

The classifier is diagnostic only. It does not rematch signals and does not widen the 45-minute / 5-pip contract.

For each unmatched outcome it reports:

```text
same-direction replay events within frozen 45-minute window
Policy-A accepted same-direction replay events within frozen 45-minute window
reject stage / filter reasons / H1 tag / H4+D1 votes
score / ADX / RSI / replay entry
nearest same-direction event within a separate 180-minute diagnostic window
nearest Policy-A event by time and by entry within that diagnostic window
```

The 180-minute window is explicitly **not** a new matching tolerance. It is only a bounded near-miss inspection window.

Primary classifications are:

```text
NO_SAME_DIRECTION_EVENT_WITHIN_45M
LIVE_PUBLISHED_BUT_REPLAY_NOT_ACCEPTED_WITHIN_45M
REPLAY_ACCEPTED_WITHIN_45M_BUT_ENTRY_DIFF_GT_5P
```

If a genuine Policy-A event satisfying the original 45-minute + 5-pip contract is found for an outcome the canonical matcher called unmatched, the classifier fails closed as a matcher inconsistency.

## Scope lock

Until the four gaps are classified and robustness/full outcome resolution completes:

```text
DO_NOT_WIDEN_MATCH_TOLERANCES=YES
DO_NOT_MUTATE_ADX_RULE=YES
DO_NOT_MUTATE_RSI_RULE=YES
DO_NOT_LOWER_SCORE_FLOOR=YES
DO_NOT_LOWER_H1_FLOOR=YES
DO_NOT_CHANGE_TELEGRAM_FLOORS=YES
DO_NOT_REMOVE_COOLDOWN=YES
DO_NOT_ADD_THIRD_PAIR=YES
DO_NOT_FIX_H1_ADX_OVERRIDE_IN_PRODUCTION_YET=YES
```

## Exactly one next action after reviewed merge

Run the reviewed gap classifier once against the already-preserved canonical `events.jsonl`, `outcome_comparison.json`, and frozen Supabase fixture, with both local SHA-256 values enforced.

Use the result to determine which live-vs-replay gate caused each of the four missing reconstructions. Do not rerun the historical acquisition or deterministic replay.
