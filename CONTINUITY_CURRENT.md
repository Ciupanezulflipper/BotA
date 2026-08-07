# BotA Current Continuity State

Last updated: 2026-08-07 18:15 UTC

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

The watcher is live. This ownership defect remains real but does not explain signal scarcity by itself.

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

## Local March component/outcome audit — verified 2026-08-07 18:15 UTC

The stale/narrow 51-row local ledger nevertheless joined completely to extended alert components:

```text
LEDGER_ROWS=51
JOINED=51
UNMATCHED=0
JOIN_RATE=100.00%
JOINED_WITH_COMPONENTS=51
WINS=13
LOSSES=38
TOTAL_PIPS=-264.1
```

Score calibration:

```text
<70:   n=11 WR=18.2% PIPS=-83.5
70-74: n=4  WR=50.0% PIPS=+2.1
75-84: n=19 WR=31.6% PIPS=-44.8
85+:   n=17 WR=17.6% PIPS=-137.9
```

RSI state:

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

This is the strongest component-level evidence so far. Current scoring awards maximum ADX contribution for ADX >=30, while the March 30-39 band was the worst-performing group. Current RSI scoring also rewards increasing distance from 50, while extreme RSI was dramatically worse than the intermediate stretched zone.

## Interpretation

The scoring model appears to reward trend intensity beyond the point where entry quality deteriorates. The likely calibration problem is non-linearity/late-entry risk rather than simple lack of signal generation.

The March sample is only about 17.5 hours, so it cannot by itself define a production replacement formula. It is historical diagnostic evidence, not current validation.

## Scope lock

Do not lower score or H1 thresholds, lower Telegram minimum, remove cooldown, add a third pair, or mutate ADX/RSI scoring yet.

## Evidence

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

Run a read-only counterfactual on the joined March rows and recent component-matched published outcomes. Test simple ADX/RSI candidate corrections and compare retained count, win rate, and total pips before any live strategy mutation.
