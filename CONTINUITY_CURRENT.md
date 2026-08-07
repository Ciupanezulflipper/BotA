# BotA Current Continuity State

Last updated: 2026-08-07 18:38 UTC

## Authoritative identifiers

```text
RECORDED_DATE=2026-08-07
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=73b2306b5843f3396823ce815e96051abf78cf50
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_SERVICE_DAEMON_PIDFILE=31140
```

## Runtime state

```text
manager_count=1
manager_pid=31140
required=7
owned=6
running=7
orphaned=1
duplicate_service_rows=0
healthy=false
orphan_service=crond
```

The watcher is live. Runtime ownership remains degraded but is not the current signal-quality root cause.

## Current effective settings

```text
PAIRS=EURUSD GBPUSD
TIMEFRAMES=M15
FILTER_SCORE_MIN=65
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

Only two pairs are live.

## Strategy funnel

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 524 survive score
  -> 410 rejected by H1-neutral veto
  -> 114 survive H1
  -> 4 rejected by H4+D1 opposition
  -> 110 strategy-accepted
```

## Accepted -> Telegram funnel

```text
61 sent
38 cooldown-suppressed
6 Telegram score-gated
1 send failure
```

Four of the 110 accepted CSV rows remain delivery-unknown.

## Recent delivered-signal quality

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

Recent high scores are not reliably separating winners from losers.

## March component/outcome sample

The 51 local March outcomes joined 100% to extended alert components:

```text
LEDGER_ROWS=51
JOINED=51
WINS=13
LOSSES=38
TOTAL_PIPS=-264.1
```

Key component splits:

```text
ADX 20-29: n=17 WR=52.9% PIPS=+98.0
ADX 30-39: n=26 WR=7.7% PIPS=-319.1
ADX 40+:   n=8  WR=25.0% PIPS=-43.0

RSI EXTREME:   n=18 WR=11.1% PIPS=-229.2
RSI STRETCHED: n=11 WR=45.5% PIPS=+69.4
RSI MODERATE:  n=22 WR=27.3% PIPS=-104.3

score 85+: n=17 WR=17.6% PIPS=-137.9
```

## ADX / RSI counterfactual — 2026-08-07 18:38 UTC

```text
BASELINE: N=51 W=13 L=38 WR=25.5% PIPS=-264.1
SCORE>=70: N=40 W=11 L=29 WR=27.5% PIPS=-180.6
NO_EXTREME_RSI: N=33 W=11 L=22 WR=33.3% PIPS=-34.9
ADX<30: N=17 W=9 L=8 WR=52.9% PIPS=+98.0
ADX<30 + NO_EXTREME: N=12 W=7 L=5 WR=58.3% PIPS=+94.8
SCORE>=70 + ADX<30: N=12 W=9 L=3 WR=75.0% PIPS=+174.2
SCORE>=70 + ADX<30 + NO_EXTREME: N=7 W=7 L=0 WR=100.0% PIPS=+171.0
```

The last subset is not production proof. It is only seven trades and was selected on the same data used to discover the rule. Treat it as high overfit risk.

The broad evidence supports a simpler diagnosis: current scoring over-rewards trend intensity and under-prices late-entry/exhaustion risk. ADX >=30 is the strongest historical warning; extreme RSI is a secondary warning.

## Scope lock

Do not lower score/H1/Telegram thresholds, remove cooldown, add a third pair, or mutate ADX/RSI scoring from this in-sample result.

## Evidence

- `audits/ADX_RSI_COUNTERFACTUAL_2026-08-07.md`
- `audits/MARCH_COMPONENT_OUTCOMES_2026-08-07.md`
- `audits/LOCAL_SIGNAL_LEDGER_INVENTORY_2026-08-07.md`
- `audits/COOLDOWN_AND_SIGNAL_QUALITY_2026-08-07.md`
- `audits/SIGNAL_DELIVERY_FUNNEL_2026-08-07.md`
- `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`
- `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
- `AI_START_HERE.md`
- `CHAT_HANDOFF_BOTA.md`
- `audits/ERROR_LOG.md`
- `ERRORS.md`

## Exactly one next action

Run a separate out-of-sample replay with candidate policies frozen before outcomes are examined:

```text
A: current baseline
B: score >=70 AND ADX <30
C: score >=70 AND ADX <30 AND no extreme RSI
```

Compare retained signal count, win/loss, total pips, and preferably MAE/MFE. Only an out-of-sample improvement can justify a production strategy mutation.
