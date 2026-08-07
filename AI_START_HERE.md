# BotA AI Start Here

Last updated: 2026-08-07 18:58 UTC

Read this before proposing BotA commands, code, cron, service, strategy, notification, provider, Supabase, or deployment changes.

## Current authoritative truth

```text
RECORDED_DATE=2026-08-07
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=73b2306b5843f3396823ce815e96051abf78cf50
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_CONTROL_PLANE=DEGRADED_6_OWNED_1_ORPHAN
CURRENT_REQUIRED_RUNNING=7_OF_7
CURRENT_ORPHAN_SERVICE=crond
LIVE_WATCHER=RUNNING
LIVE_PAIRS=EURUSD_GBPUSD_ONLY
LIVE_TIMEFRAME=M15
FILTER_SCORE_MIN_ALL=65
H1_TREND_MIN_SCORE=40
H1_VETO_OVERRIDE_SCORE=75
TELEGRAM_MIN_SCORE=70
TELEGRAM_TIER_YELLOW_MIN=70
TELEGRAM_TIER_GREEN_MIN=75
TELEGRAM_COOLDOWN_SECONDS=1800
DRY_RUN_MODE=0
TELEGRAM_ENABLED=1
BUY_SELL_VALID_ROWS=1427
BUY_SELL_ACCEPTED=110
BUY_SELL_REJECTED=1317
REJECTED_SCORE_GATE=903
REJECTED_H1_NEUTRAL=410
REJECTED_H4_D1_OPPOSE=4
TELEGRAM_SENT=61
TELEGRAM_COOLDOWN=38
TELEGRAM_SCORE_GATE=6
TELEGRAM_FAILED=1
RECENT_DELIVERED_SINCE_2026_06_01=13
RECENT_WINS=3
RECENT_LOSSES=9
RECENT_CANCELLED=1
RECENT_TOTAL_PIPS=-71.40
LOCAL_LEDGER_ROWS=51
LOCAL_LEDGER_JOIN_RATE=100_PERCENT
MARCH_TOTAL_PIPS=-264.1
MARCH_ADX_LT30_PIPS=+98.0
MARCH_SCORE70_ADX_LT30_PIPS=+174.2
TEMPORAL_PUBLISHED=13
TEMPORAL_MATCHED=9
TEMPORAL_MATCH_RATE=69.2_PERCENT
TEMPORAL_MATCHED_BASELINE_PIPS=-70.2
TEMPORAL_ADX_LT30_PIPS=+13.1
TEMPORAL_ADX_LT30_NO_EXTREME_PIPS=+28.9
TEMPORAL_ADX_GTE30_WINS=0
TEMPORAL_ADX_GTE30_LOSSES=4
UNMATCHED_TARGETS=4
UNMATCHED_RELAXED_MATCHES=0
UNMATCHED_RELAXED_COMPONENT_MATCHES=0
LOCAL_RETENTION_GAP=CONFIRMED
STRATEGY_MUTATION_ALLOWED=NO_PENDING_TRUE_REPLAY
```

## Evidence order

1. `audits/LOCAL_RETENTION_GAP_2026-08-07.md`
2. `audits/JUNE_JULY_ADX_RSI_TEMPORAL_CROSSCHECK_2026-08-07.md`
3. `audits/ADX_RSI_COUNTERFACTUAL_2026-08-07.md`
4. `audits/MARCH_COMPONENT_OUTCOMES_2026-08-07.md`
5. `audits/LOCAL_SIGNAL_LEDGER_INVENTORY_2026-08-07.md`
6. `audits/COOLDOWN_AND_SIGNAL_QUALITY_2026-08-07.md`
7. `audits/SIGNAL_DELIVERY_FUNNEL_2026-08-07.md`
8. `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`
9. `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
10. `CONTINUITY_CURRENT.md`
11. `CHAT_HANDOFF_BOTA.md`
12. `audits/ERROR_LOG.md`
13. `ERRORS.md`

## Signal funnel

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 524 survive M15 score gate
  -> 410 rejected by H1-neutral veto
  -> 114 survive H1
  -> 4 rejected by H4+D1 opposition
  -> 110 strategy-accepted
```

Retained accepted-to-Telegram evidence:

```text
106 matched accepted events
  -> 6 Telegram score-gated
  -> 38 cooldown-suppressed
  -> 1 send failure
  -> 61 sent
```

Telegram transport works and is not the dominant signal-quality problem.

## Recent delivered quality

Read-only Supabase BotA M15 outcome evidence created on or after 2026-06-01:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
75-84_TOTAL_PIPS=-36.40
85+_TOTAL_PIPS=-35.00
```

High score is not reliably separating winners from losers.

## March component/outcome evidence

The 51-row local March ledger joined 100% to extended alert components:

```text
BASELINE: N=51 W=13 L=38 WR=25.5% PIPS=-264.1
ADX<30: N=17 W=9 L=8 WR=52.9% PIPS=+98.0
SCORE>=70 + ADX<30: N=12 W=9 L=3 WR=75.0% PIPS=+174.2
SCORE>=70 + ADX<30 + NO_EXTREME: N=7 W=7 L=0 WR=100.0% PIPS=+171.0
```

The 7/7 subset is in-sample and high-overfit risk. Do not call it a 100% strategy.

## June-July temporal cross-check

Frozen March-derived policies were tested against later published outcomes. Nine of 13 published signals matched retained local component rows:

```text
PUBLISHED=13
MATCHED=9
UNMATCHED=4
MATCH_RATE=69.2%
A_CURRENT_MATCHED_BASELINE: N=9 W=2 L=7 PIPS=-70.2
B_SCORE70_ADX_LT30: N=5 W=2 L=3 PIPS=+13.1
C_SCORE70_ADX_LT30_NO_EXTREME: N=4 W=2 L=2 PIPS=+28.9
ADX_30_39: N=3 W=0 L=3 PIPS=-57.4
ADX_40_PLUS: N=1 W=0 L=1 PIPS=-25.9
```

The later-period subset points in the same direction as March, but 69.2% match coverage is insufficient for production approval.

## Local retention gap — 2026-08-07 18:58 UTC

The four unmatched June 23-26 published outcomes were searched again with a wider local-candidate window.

```text
TARGETS_TOTAL=4
TARGETS_WITH_NEARBY_ROWS=1
TARGETS_WITH_RELAXED_MATCH=0
TARGETS_WITH_RELAXED_COMPONENT_MATCH=0
VERDICT=LOCAL_RETENTION_GAP_CONFIRMED
```

Three targets had no same-pair/same-direction M15 rows within +/-2 days. The one target with nearby rows had no plausible identity match. Therefore the full 13-signal component validation cannot be reconstructed from the retained `alerts.csv`.

Stop trying to recover those four rows from this file. The missing rows are now an observability/retention gap, not a tolerance problem.

## Supabase timestamp caution

Exact Supabase `created_at` values do not line up directly with several already-matched local watcher decision timestamps. Do not use `created_at` as the original decision timestamp unless publication-time semantics are proven.

## Scope lock

Do not lower score/H1/Telegram floors, remove cooldown, add a third pair, or modify ADX/RSI production logic yet.

Do not use `tools/backtest_bota.py` as production-rule validation because its strategy implementation differs from the live watcher path.

Never push directly to `main`. Use branch -> complete content -> verified diff -> PR.

## Exactly one next action

Run a true historical replay from raw candles through the live production scoring/fusion semantics with frozen policies:

```text
A: current production baseline
B: score >=70 AND ADX <30
C: score >=70 AND ADX <30 AND no extreme RSI
```

Compare signal count, wins/losses, total pips, and preferably MAE/MFE. No production mutation before that replay.
