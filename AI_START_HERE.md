# BotA AI Start Here

Last updated: 2026-08-07 18:38 UTC

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
LOCAL_LEDGER_WINS=13
LOCAL_LEDGER_LOSSES=38
LOCAL_LEDGER_JOIN_RATE=100_PERCENT
MARCH_TOTAL_PIPS=-264.1
MARCH_ADX_LT30_PIPS=+98.0
MARCH_SCORE70_ADX_LT30_PIPS=+174.2
MARCH_SCORE70_ADX_LT30_WR=75.0_PERCENT
MARCH_SCORE70_ADX_LT30_NO_EXTREME_N=7
MARCH_SCORE70_ADX_LT30_NO_EXTREME_WR=100_PERCENT_IN_SAMPLE_ONLY
STRATEGY_MUTATION_ALLOWED=NO_PENDING_OUT_OF_SAMPLE_REPLAY
```

## Evidence order

1. `audits/ADX_RSI_COUNTERFACTUAL_2026-08-07.md`
2. `audits/MARCH_COMPONENT_OUTCOMES_2026-08-07.md`
3. `audits/LOCAL_SIGNAL_LEDGER_INVENTORY_2026-08-07.md`
4. `audits/COOLDOWN_AND_SIGNAL_QUALITY_2026-08-07.md`
5. `audits/SIGNAL_DELIVERY_FUNNEL_2026-08-07.md`
6. `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`
7. `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
8. `CONTINUITY_CURRENT.md`
9. `CHAT_HANDOFF_BOTA.md`
10. `audits/ERROR_LOG.md`
11. `ERRORS.md`

## Current signal funnel

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 524 survive score
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

Telegram transport is not the dominant failure.

## Recent delivered quality

Read-only Supabase evidence for BotA M15 signals created on or after 2026-06-01:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
75-84_TOTAL_PIPS=-36.40
85+_TOTAL_PIPS=-35.00
```

High score is not currently demonstrating reliable recent calibration.

## March component/outcome evidence

The 51-row local March ledger joined 100% to extended alert components:

```text
JOINED=51
UNMATCHED=0
WINS=13
LOSSES=38
TOTAL_PIPS=-264.1
```

The strongest component splits were:

```text
ADX 20-29: +98.0 pips, 52.9% WR
ADX 30-39: -319.1 pips, 7.7% WR
RSI extreme: -229.2 pips, 11.1% WR
RSI stretched: +69.4 pips, 45.5% WR
score 85+: -137.9 pips, 17.6% WR
```

## Counterfactual — 2026-08-07 18:38 UTC

Fixed read-only policies on the same 51 March rows produced:

```text
BASELINE: N=51 W=13 L=38 WR=25.5% PIPS=-264.1
SCORE>=70: N=40 W=11 L=29 WR=27.5% PIPS=-180.6
NO_EXTREME_RSI: N=33 W=11 L=22 WR=33.3% PIPS=-34.9
ADX<30: N=17 W=9 L=8 WR=52.9% PIPS=+98.0
ADX<30 + NO_EXTREME: N=12 W=7 L=5 WR=58.3% PIPS=+94.8
SCORE>=70 + ADX<30: N=12 W=9 L=3 WR=75.0% PIPS=+174.2
SCORE>=70 + ADX<30 + NO_EXTREME: N=7 W=7 L=0 WR=100.0% PIPS=+171.0
```

Do not interpret the 7/7 subset as a 100% strategy. It was discovered and evaluated on the same narrow 17.5-hour sample and is highly vulnerable to overfitting.

The broader directional evidence is that current ADX scoring likely rewards mature/late trends too aggressively. Extreme RSI also appears harmful. The score appears to measure trend intensity more strongly than entry quality.

## Scope lock

Do not lower score/H1/Telegram floors, remove cooldown, add a third pair, or modify ADX/RSI production logic from this in-sample result.

Never push directly to `main`. Use branch -> complete content -> verified diff -> PR.

## Exactly one next action

Run an out-of-sample historical replay over a separate period not used to discover the rule. Freeze these candidates before seeing outcomes:

```text
A: current production baseline
B: score >=70 AND ADX <30
C: score >=70 AND ADX <30 AND no extreme RSI
```

Compare signal count, wins/losses, total pips, and ideally MAE/MFE. Only then consider a production strategy change.
