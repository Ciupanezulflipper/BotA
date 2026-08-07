# BotA AI Start Here

Last updated: 2026-08-07 17:54 UTC

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
STRATEGY_MUTATION_ALLOWED=NO_PENDING_COMPONENT_OUTCOME_AUDIT
```

## Evidence order

1. `audits/COOLDOWN_AND_SIGNAL_QUALITY_2026-08-07.md`
2. `audits/SIGNAL_DELIVERY_FUNNEL_2026-08-07.md`
3. `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`
4. `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
5. `CONTINUITY_CURRENT.md`
6. `CHAT_HANDOFF_BOTA.md`
7. `audits/ERROR_LOG.md`
8. `ERRORS.md`

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

## Cooldown interpretation — corrected 2026-08-07 17:54 UTC

The 38 cooldown-suppressed accepted events were compared with the last sent event for the same pair/timeframe:

```text
EXACT_DUPLICATE=0
NOT_EXACT_DUPLICATE=38
DIRECTION_CHANGED=0
SCORE_IMPROVED_5PLUS=7
ENTRY_CHANGED_3PLUS_PIPS=26
```

Do not call these 38 `new trades`. They are field-level different but all remain the same direction as the preceding sent signal. The current 30-minute cooldown is coarse and keyed only by pair/timeframe, while exact content dedup runs later. It may suppress meaningful updates, but it also clearly acts as repeat-alert suppression. Do not remove it blindly.

## Signal quality cross-check — new highest priority

Read-only Supabase outcome data for BotA M15 rows with rationale `BotA score=` shows:

```text
historical score <70: n=6, wins=1, losses=5, total_pips=-45.50
historical 70-74:    n=3, wins=2, losses=1, total_pips=+59.60
historical 75-84:   n=33, wins=12, losses=17, cancelled=4, total_pips=+56.10
historical 85+:     n=16, wins=4, losses=10, cancelled=2, total_pips=+25.10
```

Most important: delivered BotA M15 signals created on or after 2026-06-01 are currently:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
```

Recent higher scores did not solve this:

```text
75-84: n=11, wins=3, losses=7, cancelled=1, total_pips=-36.40
85+:   n=2, wins=0, losses=2, total_pips=-35.00
```

Therefore the current problem is not merely `too few messages`. Recent accepted/delivered signal edge is poor. Increasing signal volume before diagnosing score-component/regime quality would be the wrong repair.

## Current live configuration

```text
PAIRS=EURUSD GBPUSD
TIMEFRAMES=M15
FILTER_SCORE_MIN_ALL=65
H1_VETO_OVERRIDE_SCORE=75
TELEGRAM_MIN_SCORE=70
TELEGRAM_TIER_YELLOW_MIN=70
TELEGRAM_TIER_GREEN_MIN=75
TELEGRAM_COOLDOWN_SECONDS=1800
```

Only two pairs are live. A third pair requires explicit validation and configuration later.

## Closed/non-dominant causes

- Zero entry/SL/TP: HOLD symptom only; no BUY/SELL zero-entry rows.
- `macro6=3`: neutral in current fusion code.
- RR text: advisory in current quality filter.
- H4+D1 opposition: only four valid BUY/SELL rejects.
- Telegram transport: 61 successful retained sends versus one failure.

## Scope lock

Do not lower score/H1/Telegram floors, remove cooldown, or add a third pair merely to increase signal count.

Keep current protections until recent delivered losers are joined to their 25-column decision components and the misleading component/regime is identified.

Never push directly to `main`. Use branch -> complete content -> verified diff -> PR.

## Exactly one next action

For delivered M15 signals since 2026-06-01, extract the alert-row components (`ema_comp`, `rsi_comp`, `macd_comp`, `adx_comp`, raw ADX/RSI/MACD, H1 trend, tier, session, ADX regime) and compare them with verified Supabase outcomes. Identify the first component or regime that explains the recent losses before changing signal volume policy.
