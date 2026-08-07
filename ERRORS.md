# BotA Errors and Silent-Failure Register

Last updated: 2026-08-07 18:09 UTC

Purpose: preserve verified failure classes, current open risks, and prevention rules without repeating broad audits.

Current signal evidence:

- `audits/LOCAL_SIGNAL_LEDGER_INVENTORY_2026-08-07.md`
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
RECENT_DELIVERED_SINCE_2026_06_01=13
RECENT_WINS=3
RECENT_LOSSES=9
RECENT_CANCELLED=1
RECENT_TOTAL_PIPS=-71.40
LOCAL_LEDGER_ROWS=51
LOCAL_LEDGER_WINS=13
LOCAL_LEDGER_LOSSES=38
LOCAL_LEDGER_CURRENTNESS=STALE_NARROW
STRATEGY_MUTATION_ALLOWED=NO_PENDING_COMPONENT_OUTCOME_AUDIT
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

## Signal outcome quality risk

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

Recent high scores are not showing reliable calibration. Increasing signal count is not a sufficient repair.

## Local ledger limitation — 2026-08-07 18:09 UTC

Verified phone inventory:

```text
PATH=data/ledger.csv
LEDGER_ROWS=51
WIN=13
LOSS=38
WIN_RATE=25.49%
FIRST_TIMESTAMP=2026-03-09T21:45:07+02:00
LAST_TIMESTAMP=2026-03-10T15:15:07+02:00
```

The ledger is stale and narrow: approximately 17.5 hours of March data. It must not be silently treated as current June-August performance. Its valid use is a bounded historical component/outcome join if extended alert rows match.

## Current scoring concerns under investigation

- RSI contribution is based on absolute distance from 50 and can reward extreme oversold SELL or overbought BUY conditions up to +15 points.
- Pullback code comments describe a ±0.3 ATR zone while the implementation uses a 1.0 ATR buffer.
- These are hypotheses, not approved code changes.

## Closed/non-dominant hypotheses

- zero entry/SL/TP: HOLD-only symptom;
- `macro6=3`: neutral;
- RR text: advisory;
- H4+D1 opposition: rare;
- Telegram transport: functional;
- cooldown: coarse, but not proven to hide 38 independent trades.

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

Keep this separate from signal-quality work unless watcher execution is interrupted.

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
- direct-main connector fallback violation;
- stale narrow ledger almost mistaken for current performance evidence.

## Current prevention rules

- Do not equate more Telegram messages with a repaired trading system.
- Do not lower score/H1/Telegram thresholds before outcome calibration.
- Do not call same-direction changed rows independent trades without lifecycle evidence.
- Do not treat narrow historical ledger coverage as current-strategy evidence.
- Separate March local-ledger evidence from recent June-August Supabase outcomes.
- Keep evidence packages small and dated.
- Full-file replacement only for approved mutations.
- Branch -> verified diff -> PR; never direct-main fallback.

## Exactly one next investigation

Join the 51 March ledger outcomes to matching extended alert rows and compare WIN/LOSS by score bucket, RSI extremity, MACD saturation, ADX band, H1 state, pair, and direction. First report match coverage; if coverage is poor, stop rather than infer.
