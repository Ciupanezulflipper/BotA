# BotA Current Continuity State

Last updated: 2026-08-07 17:54 UTC

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
0 tier-gated
0 exact delivery-deduped
0 dry-run/disabled
0 backoff
```

Four of the 110 accepted CSV rows have no matched retained log evidence and remain delivery-unknown.

## Cooldown semantics — verified 2026-08-07 17:54 UTC

All 38 cooldown events matched a prior successful send for the same pair/timeframe:

```text
EXACT_DUPLICATE=0
NOT_EXACT_DUPLICATE=38
DIRECTION_CHANGED=0
SCORE_IMPROVED_5PLUS=7
ENTRY_CHANGED_3PLUS_PIPS=26
UNMATCHED=0
```

The cooldown is keyed only by pair/timeframe and runs before exact content dedup. It therefore suppresses field-level changed same-direction updates. Because direction never changed, this audit does not prove that 38 independent new trade opportunities were lost.

## Supabase delivered-signal quality cross-check

Read-only query of `public.signals` for M15 rows whose rationale begins `BotA score=`:

```text
score <70:  n=6,  wins=1, losses=5, cancelled=0, total_pips=-45.50
score 70-74: n=3, wins=2, losses=1, cancelled=0, total_pips=+59.60
score 75-84: n=33, wins=12, losses=17, cancelled=4, total_pips=+56.10
score 85+:   n=16, wins=4, losses=10, cancelled=2, total_pips=+25.10
```

The `<70` sample is small but negative, so removing the Telegram 70 floor is not currently supported.

### Recent signals since 2026-06-01

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
```

By score:

```text
75-84: n=11, wins=3, losses=7, cancelled=1, total_pips=-36.40
85+:   n=2, wins=0, losses=2, cancelled=0, total_pips=-35.00
```

This is now the highest-priority finding. Recent accepted/delivered M15 signals have poor outcomes even at high scores. Signal count alone is not the product defect; score/regime quality must be diagnosed before loosening gates.

## Closed/non-dominant hypotheses

- zero entry: HOLD-only symptom;
- `macro6=3`: neutral tag;
- RR text: advisory;
- H4+D1 opposition: rare;
- Telegram transport: functioning;
- cooldown: coarse, but not proven to have hidden 38 independent new trades.

## Scope lock

Do not lower score or H1 thresholds, lower Telegram minimum, remove cooldown, or add a third pair merely to manufacture volume.

## Evidence

- `audits/COOLDOWN_AND_SIGNAL_QUALITY_2026-08-07.md`
- `audits/SIGNAL_DELIVERY_FUNNEL_2026-08-07.md`
- `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`
- `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
- `AI_START_HERE.md`
- `CHAT_HANDOFF_BOTA.md`
- `audits/ERROR_LOG.md`
- `ERRORS.md`

## Exactly one next action

Extract the 25-column decision components for delivered M15 signals since 2026-06-01 and correlate those components with the verified Supabase outcomes. Identify which scoring component/regime is misleading the score before any signal-volume change.
