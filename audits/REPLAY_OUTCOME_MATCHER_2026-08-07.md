# BotA Replay-to-Published-Outcome Matching Contract

Recorded date: **2026-08-07**

## Purpose

Define the matching rules **before** the canonical local replay event ledger is compared with the frozen June-July Supabase published outcomes.

This prevents post-result tolerance tuning and prevents Supabase publication timestamps from being treated as signal identity.

## Inputs

Canonical replay event ledger:

```text
data/replay_results/phase2-june-july-pr64/events.jsonl
EXPECTED_EVENTS_SHA256=05089e6d97e4ab9f3a522d9ec1188c24e69637bf048f1cd1403f23772ec8dabc
```

Frozen database snapshot:

```text
audits/fixtures/supabase_bota_m15_20260601_20260801.json
SOURCE=public.signals via Supabase connector
WINDOW=[2026-06-01T00:00:00Z,2026-08-01T00:00:00Z)
EXPECTED_OUTCOMES=13
```

## Frozen matching contract

A replay event is a candidate for one published outcome only when all of the following hold:

```text
POLICY_A_CURRENT=TRUE
PAIR=EXACT
DIRECTION=EXACT
ENTRY_ABSOLUTE_DIFFERENCE<=5.0_PIPS
ABS(PUBLISHED_CREATED_AT-REPLAY_DECISION_TIME)<=45_MINUTES
```

`created_at` is publication time and is explicitly forbidden as a sole identity key.

The 45-minute bound allows multiple M15 polling/publication cycles without making the timestamp itself the identity. The 5-pip entry bound is deliberately small enough to require price consistency while allowing minor historical/provider/runtime price differences.

These tolerances are frozen before the canonical local comparison result is observed. If matching fails, do not automatically widen them. Classify unmatched/ambiguous cases first.

## Conservative assignment rule

The matcher performs one-to-one assignment only when a candidate is uniquely resolvable under the frozen constraints.

```text
ONE_REPLAY_EVENT_PER_PUBLISHED_SIGNAL=REQUIRED
ONE_PUBLISHED_SIGNAL_PER_REPLAY_EVENT=REQUIRED
AMBIGUOUS_MATCH=REPORT_NOT_FORCE
UNMATCHED_SIGNAL=REPORT
```

The resolver may iteratively remove already-consumed unique replay events. If multiple unresolved candidates remain after deterministic elimination, the published outcome remains ambiguous.

No nearest-neighbor fallback is allowed merely to reach 13/13.

## Match gate

```text
MATCH_GATE=PASS
```

requires:

```text
PUBLISHED_OUTCOMES=13
MATCHED_OUTCOMES=13
UNMATCHED_OUTCOMES=0
AMBIGUOUS_OUTCOMES=0
```

Anything else is a valid forensic result but a failed completeness gate.

## Policy statistics

Only after matching, each real published outcome is classified by whether its uniquely matched replay event passes frozen policies A/B/C:

```text
A = current production acceptance
B = A AND score >=70 AND ADX <30
C = B AND no extreme RSI
```

The tool reports wins, losses, cancellations and total published pips for each policy subset.

These statistics are **observed published-outcome counterfactuals**, not a full PnL backtest of all replay events. Replay produced 105/51/45 A/B/C accepted events, while only 13 real published signals have Supabase outcome truth in this interval.

A later full replay outcome-resolution model is required before claiming performance for all replay-only candidate events.

## Safety contract

The matcher is offline and does not query Supabase, OANDA, Telegram, or any other network service at runtime.

It reads the immutable local replay event ledger and frozen JSON snapshot, then writes only the explicit comparison output selected by the operator.

It must not mutate production strategy, thresholds, pair scope, Telegram, Supabase, services, cron, cooldown state, or the production candle cache.

## Next action after reviewed merge

Run the reviewed matcher once against the canonical event ledger with the exact expected event SHA-256 and frozen tolerances above.

If `MATCH_GATE=PASS`, record the exact A/B/C observed published-outcome comparison and proceed to robustness/full replay trade-outcome resolution.

If `MATCH_GATE=FAIL`, preserve the output and classify unmatched/ambiguous cases before any matching-contract or strategy change.
