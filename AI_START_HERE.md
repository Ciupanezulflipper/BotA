# BotA AI Start Here

Last updated: 2026-08-07 18:09 UTC

Read this before proposing BotA commands, code, cron, service, strategy,
notification, provider, Supabase, or deployment changes.

## Current authoritative truth

```text
RECORDED_DATE=2026-08-07
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=73b2306b5843f3396823ce815e96051abf78cf50
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_CONTROL_PLANE=DEGRADED_6_OWNED_1_ORPHAN
CURRENT_REQUIRED_RUNNING=7_OF_7
CURRENT_ORPHAN_SERVICE=crond
CURRENT_DUPLICATE_SERVICE_ROWS=0
LIVE_WATCHER=RUNNING
LIVE_PAIRS=EURUSD_GBPUSD_ONLY
LIVE_TIMEFRAME=M15
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
BUY_SELL_VALID_ROWS=1427
BUY_SELL_ACCEPTED=110
BUY_SELL_REJECTED=1317
REJECTED_SCORE_GATE=903
REJECTED_H1_NEUTRAL=410
REJECTED_H4_D1_OPPOSE=4
ACCEPTED_LOG_EVENTS_PARSED=106
TELEGRAM_SENT=61
TELEGRAM_COOLDOWN=38
TELEGRAM_SCORE_GATE=6
TELEGRAM_FAILED=1
COOLDOWN_EXACT_DUPLICATES=0
COOLDOWN_SAME_DIRECTION=38
COOLDOWN_DIRECTION_REVERSALS=0
COOLDOWN_ENTRY_CHANGED_3PLUS_PIPS=26
COOLDOWN_SCORE_IMPROVED_5PLUS=7
RECENT_DELIVERED_SINCE_2026_06_01=13
RECENT_WINS=3
RECENT_LOSSES=9
RECENT_CANCELLED=1
RECENT_TOTAL_PIPS=-71.40
LOCAL_LEDGER_ROWS=51
LOCAL_LEDGER_WINS=13
LOCAL_LEDGER_LOSSES=38
LOCAL_LEDGER_FIRST=2026-03-09T21:45:07+02:00
LOCAL_LEDGER_LAST=2026-03-10T15:15:07+02:00
LOCAL_LEDGER_CURRENTNESS=STALE_NARROW
STRATEGY_MUTATION_ALLOWED=NO_PENDING_COMPONENT_OUTCOME_AUDIT
```

## Evidence order

1. `audits/LOCAL_SIGNAL_LEDGER_INVENTORY_2026-08-07.md`
2. `audits/COOLDOWN_AND_SIGNAL_QUALITY_2026-08-07.md`
3. `audits/SIGNAL_DELIVERY_FUNNEL_2026-08-07.md`
4. `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`
5. `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
6. `CONTINUITY_CURRENT.md`
7. `CHAT_HANDOFF_BOTA.md`
8. `audits/ERROR_LOG.md`
9. `ERRORS.md`

## Current signal funnel

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

Telegram transport is not the dominant failure. The watcher and send path work.

## Cooldown interpretation — 2026-08-07 17:54 UTC

```text
EXACT_DUPLICATE=0
NOT_EXACT_DUPLICATE=38
DIRECTION_CHANGED=0
SCORE_IMPROVED_5PLUS=7
ENTRY_CHANGED_3PLUS_PIPS=26
```

The 38 rows are non-identical same-direction accepted updates, not proven independent new trades. Do not remove cooldown blindly.

## Signal quality cross-check — highest priority

Read-only Supabase outcome data for BotA M15 rows with rationale `BotA score=` shows recent signals created on or after 2026-06-01:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
75-84: n=11, wins=3, losses=7, cancelled=1, total_pips=-36.40
85+:   n=2, wins=0, losses=2, total_pips=-35.00
```

High score is not currently demonstrating reliable recent calibration.

## Local signal ledger inventory — 2026-08-07 18:09 UTC

The phone already has `data/ledger.csv`, but its coverage is narrow and stale:

```text
LEDGER_ROWS=51
WIN=13
LOSS=38
WIN_RATE=25.49%
FIRST_TIMESTAMP=2026-03-09T21:45:07+02:00
LAST_TIMESTAMP=2026-03-10T15:15:07+02:00
```

This is only about 17.5 hours of March data. It is useful as a historical component/outcome sample if it joins cleanly to the 25-column alert rows, but it must not be treated as current June-August strategy performance.

## Scoring-engine warning under investigation

Current source computes RSI contribution as:

```text
rsi_comp = min(15.0, abs(rsi - 50.0) * 0.6)
```

This rewards RSI extremity in either direction. Current source also comments on a ±0.3 ATR pullback zone while using a 1.0 ATR buffer. These are hypotheses for false confidence, not yet approved defects.

## Scope lock

Do not lower score/H1/Telegram floors, remove cooldown, or add a third pair merely to increase signal count.

Never push directly to `main`. Use branch -> complete content -> verified diff -> PR.

## Exactly one next action

Join the 51 local ledger outcomes to matching 25-column `logs/alerts.csv` rows. Report match coverage and compact WIN/LOSS splits by score bucket, RSI extremity, MACD saturation, ADX band, H1 state, pair, and direction. Keep March findings separate from the newer Supabase outcome evidence.
