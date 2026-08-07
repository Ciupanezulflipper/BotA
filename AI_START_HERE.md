# BotA AI Start Here

Last updated: 2026-08-07 18:15 UTC

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
MARCH_ADX_20_29_PIPS=+98.0
MARCH_ADX_30_39_PIPS=-319.1
MARCH_RSI_EXTREME_PIPS=-229.2
MARCH_RSI_STRETCHED_PIPS=+69.4
MARCH_SCORE_85PLUS_PIPS=-137.9
STRATEGY_MUTATION_ALLOWED=NO_PENDING_COUNTERFACTUAL_AUDIT
```

## Evidence order

1. `audits/MARCH_COMPONENT_OUTCOMES_2026-08-07.md`
2. `audits/LOCAL_SIGNAL_LEDGER_INVENTORY_2026-08-07.md`
3. `audits/COOLDOWN_AND_SIGNAL_QUALITY_2026-08-07.md`
4. `audits/SIGNAL_DELIVERY_FUNNEL_2026-08-07.md`
5. `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`
6. `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
7. `CONTINUITY_CURRENT.md`
8. `CHAT_HANDOFF_BOTA.md`
9. `audits/ERROR_LOG.md`
10. `ERRORS.md`

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

## March component/outcome audit — 2026-08-07 18:15 UTC

The 51-row local March ledger joined 100% to extended alert components:

```text
JOINED=51
UNMATCHED=0
JOINED_WITH_COMPONENTS=51
WINS=13
LOSSES=38
TOTAL_PIPS=-264.1
```

Score bucket outcome:

```text
<70:   WR=18.2% PIPS=-83.5
70-74: WR=50.0% PIPS=+2.1
75-84: WR=31.6% PIPS=-44.8
85+:   WR=17.6% PIPS=-137.9
```

The highest score bucket was the worst, so score magnitude was not monotonically calibrated to outcome quality in this sample.

RSI entry state:

```text
EXTREME:   n=18 WR=11.1% PIPS=-229.2
STRETCHED: n=11 WR=45.5% PIPS=+69.4
MODERATE:  n=22 WR=27.3% PIPS=-104.3
```

ADX band:

```text
20-29: n=17 WR=52.9% PIPS=+98.0
30-39: n=26 WR=7.7%  PIPS=-319.1
40+:   n=8  WR=25.0% PIPS=-43.0
```

This is the strongest historical component split. Current source awards maximum ADX points at ADX >=30, while the 30-39 band was catastrophically poor in this March sample.

Current source also rewards absolute RSI distance from 50. In this March sample, the intermediate stretched zone was the only positive RSI-state group while extreme RSI was the worst.

## Working hypothesis

BotA appears to reward **trend intensity** more strongly than **entry quality**. The relationship is likely non-linear: stronger ADX and more extreme RSI can indicate a later, exhausted entry rather than a better one.

This hypothesis is directionally supported by the recent component-matched losses, which also include high ADX and extreme RSI examples.

## Scope lock

Do not lower score/H1/Telegram floors, remove cooldown, add a third pair, or modify ADX/RSI production logic yet.

Never push directly to `main`. Use branch -> complete content -> verified diff -> PR.

## Exactly one next action

Run a read-only counterfactual on the 51 joined March rows and the recent component-matched published signals. Compare minimal candidate policies such as penalizing extreme RSI, reducing/reversing the ADX bonus above 30, and combining both. Report retained count, win rate, and pips before any production mutation.
