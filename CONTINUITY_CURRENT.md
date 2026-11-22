# BotA Current Continuity State

Last updated: **2026-11-22 UTC**

This is the canonical operational handoff. Historical audits remain evidence; stale current-state instructions are superseded by this file.

## Current authoritative status

```text
BOTA_EDGE_STATUS=UNVALIDATED
LIVE_MONEY_TRADING=NO
PRIMARY_RUNTIME=HETZNER
RUNTIME_STATE=ACTIVE
DEPLOYED_RELEASE=83fa71e651483c95096ce635b525cacbf91cbc5d
PROVIDER=YAHOO
PAIR_SCOPE=EURUSD,GBPUSD,USDJPY
TIMEFRAME=M15
ANDROID_ACTIVE_SCANNER=NO
ANDROID_ROLE=CONTROL_AND_OBSERVATION_ONLY

PR135_RECONCILIATION=MERGED_2026-11-02
PR136_GREEN_VISIBILITY_FIX=MERGED_2026-11-02
DISTINCT_GREEN_BYPASSES_PAIR_COOLDOWN=YES
YELLOW_WATCHLIST_COOLDOWN=UNCHANGED
EXACT_SIGNAL_DEDUP=UNCHANGED

STRATEGY_TUNING=NO
PAIR_CHANGES=NO
TIMEFRAME_CHANGES=NO
FORCED_SIGNAL_GENERATION=NO

CURRENT_PHASE=OBSERVE_STORE_COLLECT_ANALYZE
NEXT_ACTION=READ_ONLY_REPORTING_AND_HEALTH_ACCOUNTING_RECONCILIATION
PRODUCTION_CHANGE_AUTHORIZED=NO
```

Runtime release identity was re-verified on 2026-11-22: `/opt/bota/current` resolves to the immutable `83fa71e651483c95096ce635b525cacbf91cbc5d` release.

Supabase runtime health at 2026-11-22 11:40 UTC reported `bota-hetzner-primary` as `HEALTHY`, with no current failure reason. 22 Nov is a closed-market Sunday, so absence of watcher progress is not a trading failure.

## Source-control state

PR #135, `Reconcile production lineage into main`, merged on 2026-11-02 with merge commit:

```text
1435fcf4441b5a5b8fb976c4164377f9d82f4f38
```

PR #136, `Keep distinct GREEN signals visible through Telegram cooldown`, merged on 2026-11-02 with merge commit / current production release:

```text
83fa71e651483c95096ce635b525cacbf91cbc5d
```

PR #136 fixed the lifecycle inconsistency proven on 30 Oct: a genuinely distinct GREEN signal is no longer hidden by the broad pair/timeframe Telegram cooldown. YELLOW/watchlist cooldown and exact identity dedup remain unchanged. No strategy, score, threshold, pair, timeframe, SL/TP or provider-policy change was made.

## Post-release GREEN lifecycle evidence

Production / Supabase evidence after `83fa71e65148...`:

| Date | Pair | Direction | Entry | Outcome | Pips |
|---|---|---|---:|---|---:|
| 2026-11-04 | USDJPY | BUY | 158.42101 | LOSS | -22.5 |
| 2026-11-11 | EURUSD | SELL | 1.11410 | WIN | +20.8 |
| 2026-11-12 | GBPUSD | SELL | 1.32456 | CANCELLED | 0.0 |

The GBPUSD trade remained ACTIVE for approximately 24 hours without TP or SL being hit, then Supabase recorded `CANCELLED` at 2026-11-13 15:25 UTC with `0.00` pips.

Post-release performance snapshot:

```text
GREEN_LIFECYCLES=3
CLOSED=2
WINS=1
LOSSES=1
CANCELLED=1
CLOSED_WIN_RATE=50.0%
CLOSED_NET_PIPS=-1.7
STRATEGY_CONCLUSION=INSUFFICIENT_SAMPLE
```

Do not tune strategy from these three lifecycles.

## Current Supabase signal ledger

Read-only Supabase snapshot on 2026-11-22:

```text
TOTAL_CLOSED=67
TOTAL_WINS=24
TOTAL_LOSSES=43
TOTAL_CANCELLED=8
TOTAL_ACTIVE=0
ALL_TIME_CLOSED_WIN_RATE=35.8%
ALL_TIME_CLOSED_NET_PIPS=+34.6
```

These are BotA signal-ledger statistics, not brokerage-account P&L.

## Reporting / observability inconsistency — OPEN

The monitoring layer is not yet internally coherent enough to treat every daily `0 signals` line as authoritative strategy evidence.

Verified examples:

- 11 Nov Daily Market Report states `0 qualified / 0 Telegram`, while production/Supabase proves a GREEN EURUSD SELL was published, tracked and closed WIN +20.8 pips that day. The same day's Proof-of-Work reports one filter-accepted / threshold-eligible candidate.
- 12 Nov Daily Market Report states `2 qualified / 2 Telegram`, while the Proof-of-Work reports `0 filter-accepted / 0 Telegram-threshold eligible`. Production proves one real GREEN GBPUSD SELL and the earlier 71.9 GBPUSD alert was a YELLOW watchlist.
- Proof-of-Work on 11-12 Nov reported API usage `960/800 (120%)` while Telegram also warned at `600/800 (75%)`. This counter must be reconciled before treating it as provider-billing truth.
- Repeated `SCAN DELAYED` / `SCAN RESTORED` notices appeared 18-20 Nov, including multi-hour delays, while the final daily reports still showed all 156 expected market-open watcher cycles. Their timing/classification must be audited before labeling them true market-open outages.

Therefore:

```text
RUNTIME_SIGNAL_GENERATION=PROVEN
GREEN_LIFECYCLE_DELIVERY=PROVEN
OUTCOME_TRACKING=PROVEN
REPORTING_ACCOUNTING_CONSISTENCY=NOT_PROVEN
SCAN_DELAY_CLASSIFICATION=NOT_PROVEN
API_USAGE_COUNTER_ACCURACY=NOT_PROVEN
```

## Strategy boundary

Do not change Policy B, score/ADX/RSI thresholds, pairs, timeframe, H1 confirmation, TP/SL rules or provider policy based on the current sample.

The current release has produced `LOSS -> WIN -> CANCELLED`. That is enough to prove the pipeline can generate and resolve natural GREEN lifecycles, but not enough to establish or reject trading edge.

## Exactly one next action

Perform one bounded **read-only reporting and health-accounting reconciliation**. Establish one canonical lifecycle ledger:

```text
GREEN SENT -> ACTIVE -> WIN | LOSS | CANCELLED
```

Then reconcile Daily Market Report, Daily Proof-of-Work, Telegram delivery, Supabase `public.signals`, API-usage accounting and scan-delay classification against that same truth.

Do not change strategy or production behavior as part of that audit.