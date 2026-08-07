# BotA Current Continuity State

Last updated: 2026-08-07 18:09 UTC

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

The watcher is live. This ownership defect remains operationally real but does not explain signal scarcity by itself.

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

Retained watcher logs classify 106 accepted events:

```text
61 sent
38 cooldown-suppressed
6 Telegram score-gated
1 send failure
```

Four of the 110 accepted CSV rows remain delivery-unknown.

## Cooldown semantics — verified 2026-08-07 17:54 UTC

```text
EXACT_DUPLICATE=0
NOT_EXACT_DUPLICATE=38
DIRECTION_CHANGED=0
SCORE_IMPROVED_5PLUS=7
ENTRY_CHANGED_3PLUS_PIPS=26
```

All 38 were same-direction accepted updates. Cooldown is coarse but is not proven to have hidden 38 independent new trades.

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

This is the highest-priority product finding. Recent high scores are not reliably separating winners from losers.

## Local signal ledger inventory — verified 2026-08-07 18:09 UTC

```text
PATH=data/ledger.csv
LEDGER_ROWS=51
WIN=13
LOSS=38
WIN_RATE=25.49%
FIRST_TIMESTAMP=2026-03-09T21:45:07+02:00
LAST_TIMESTAMP=2026-03-10T15:15:07+02:00
```

The ledger covers only about 17.5 hours. It is stale and narrow relative to the current June-August investigation. It may be useful for an offline component/outcome join if matching 25-column alert rows exist, but it cannot substitute for the recent Supabase outcome evidence.

## Current scoring hypotheses

Current `scoring_engine.sh` rewards RSI distance from 50 up to +15 points, so highly oversold SELLs and highly overbought BUYs can receive maximum RSI contribution. It also describes a ±0.3 ATR pullback zone while the implementation uses a 1.0 ATR buffer. These are hypotheses requiring outcome correlation before mutation.

## Scope lock

Do not lower score or H1 thresholds, lower Telegram minimum, remove cooldown, or add a third pair merely to manufacture volume.

## Evidence

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

Join the 51 local ledger rows to 25-column `logs/alerts.csv` rows and report match coverage plus compact outcome splits by score bucket, RSI extremity, MACD saturation, ADX band, H1 state, pair, and direction. Keep March and recent June-August evidence separate.
