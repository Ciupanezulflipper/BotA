# BotA Errors and Silent-Failure Register

Last updated: 2026-08-07 17:54 UTC

Purpose: preserve verified failure classes, current open risks, and prevention rules without repeating broad audits.

Current signal evidence:

- `audits/COOLDOWN_AND_SIGNAL_QUALITY_2026-08-07.md`
- `audits/SIGNAL_DELIVERY_FUNNEL_2026-08-07.md`
- `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`
- `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
- `CONTINUITY_CURRENT.md`
- `CHAT_HANDOFF_BOTA.md`
- `audits/ERROR_LOG.md`

## Current verdict — 2026-08-07

```text
PRODUCTION_VALIDATION=FAILED_HISTORICAL
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_CONTROL_PLANE=DEGRADED_6_OWNED_1_ORPHAN
CURRENT_REQUIRED_RUNNING=7_OF_7
LIVE_WATCHER=RUNNING
LIVE_PAIRS=EURUSD_GBPUSD_ONLY
LIVE_TIMEFRAME=M15
FILTER_SCORE_MIN_ALL=65
H1_VETO_OVERRIDE_SCORE=75
TELEGRAM_MIN_SCORE=70
TELEGRAM_COOLDOWN_SECONDS=1800
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
COOLDOWN_DIRECTION_REVERSALS=0
RECENT_DELIVERED_SINCE_2026_06_01=13
RECENT_WINS=3
RECENT_LOSSES=9
RECENT_CANCELLED=1
RECENT_TOTAL_PIPS=-71.40
STRATEGY_MUTATION_ALLOWED=NO_PENDING_COMPONENT_OUTCOME_AUDIT
AUTOMATIC_RECOVERY_REENABLE_ALLOWED=NO
```

## Current throughput finding

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 410 later rejected by H1-neutral veto
  -> 4 rejected by H4+D1 opposition
  -> 110 strategy-accepted
```

Retained delivery evidence for 106 matched accepted events:

```text
61 sent
38 cooldown-suppressed
6 Telegram score-gated
1 send failure
```

## Current live configuration finding

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

A third live pair is not configured.

## Cooldown interpretation correction

Phone audit at 2026-08-07 17:54 UTC:

```text
COOLDOWN_TOTAL=38
EXACT_DUPLICATE=0
NOT_EXACT_DUPLICATE=38
DIRECTION_CHANGED=0
SCORE_IMPROVED_5PLUS=7
ENTRY_CHANGED_3PLUS_PIPS=26
```

The cooldown is coarse because it uses pair/timeframe only and runs before exact content dedup. However, all 38 suppressed events remained the same direction as the preceding sent event. Do not represent them as 38 proven independent new trades. They are best described as non-identical same-direction accepted updates.

## Signal outcome quality risk

Read-only Supabase historical M15 BotA rows with rationale `BotA score=`:

```text
<70:   n=6,  wins=1, losses=5, total_pips=-45.50
70-74: n=3,  wins=2, losses=1, total_pips=+59.60
75-84: n=33, wins=12, losses=17, cancelled=4, total_pips=+56.10
85+:   n=16, wins=4, losses=10, cancelled=2, total_pips=+25.10
```

The `<70` sample argues against removing the current Telegram 70 floor merely to increase volume.

Delivered M15 signals since 2026-06-01:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
```

Recent high-score performance is also poor:

```text
75-84 total_pips=-36.40
85+ total_pips=-35.00
```

This is now the highest-risk strategy finding. The score is not currently demonstrating reliable recent calibration.

## Closed/non-dominant hypotheses

- zero entry/SL/TP: HOLD-only symptom;
- `macro6=3`: neutral;
- RR text: advisory;
- H4+D1 opposition: rare;
- Telegram transport: functional;
- cooldown: major suppressor, but not proven to hide 38 independent trades.

## CSV schema drift

The current alert file has a 13-column legacy header with newer 25-column rows. First 13 positions align for existing funnel audits, but named-field consumers can misclassify extended fields.

## Runtime ownership incident

Latest observed topology:

```text
manager_count=1
owned=6
orphaned=1
running=7
duplicates=0
orphan=crond
```

Keep this separate from signal-quality work unless it interrupts watcher execution.

## Historical failure classes retained

- duplicate execution ownership between cron/runit/boot paths;
- manager death with PID-1 orphan supervisors;
- canonical documentation lag;
- strict shell mode terminating interactive Termux;
- recursive scans entering runit FIFOs;
- `pipefail` aborting on expected zero matches;
- wall-clock/monotonic confusion;
- inaccessible `/proc/uptime`;
- service presence mistaken for useful progress;
- D1 timeframe mismatch;
- active service path assumed equal to repo path;
- oversized terminal packages;
- CSV field-name mismatch;
- 13-column header with 25-column rows;
- direct-main connector fallback violation.

## Current prevention rules

- Do not equate more Telegram messages with a repaired trading system.
- Do not lower score/H1/Telegram thresholds before outcome calibration.
- Do not call same-direction changed rows independent trades without lifecycle evidence.
- Validate current pair universe explicitly.
- Separate runtime, strategy, delivery, and realized outcome quality.
- Keep evidence packages small and dated.
- Full-file replacement only for approved mutations.
- Branch -> verified diff -> PR; never direct-main fallback.

## Exactly one next investigation

Join recent delivered signals to their 25-column decision components and compare component/regime values with verified outcomes. Find why high-score recent signals lost before increasing signal frequency.
