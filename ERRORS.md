# BotA Errors and Silent-Failure Register

Last updated: 2026-08-07 18:46 UTC

Purpose: preserve verified failure classes, current open risks, and prevention rules without repeating broad audits.

Current signal evidence:

- `audits/JUNE_JULY_ADX_RSI_TEMPORAL_CROSSCHECK_2026-08-07.md`
- `audits/ADX_RSI_COUNTERFACTUAL_2026-08-07.md`
- `audits/MARCH_COMPONENT_OUTCOMES_2026-08-07.md`
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
LOCAL_LEDGER_JOIN_RATE=100_PERCENT
MARCH_TOTAL_PIPS=-264.1
MARCH_ADX_LT30_PIPS=+98.0
TEMPORAL_MATCHED=9_OF_13
TEMPORAL_MATCH_RATE=69.2_PERCENT
TEMPORAL_MATCHED_BASELINE_PIPS=-70.2
TEMPORAL_ADX_LT30_PIPS=+13.1
TEMPORAL_ADX_LT30_NO_EXTREME_PIPS=+28.9
TEMPORAL_ADX_GTE30=0W_4L_MINUS83.3_PIPS
STRATEGY_MUTATION_ALLOWED=NO_PENDING_UNMATCHED_RECOVERY_OR_TRUE_REPLAY
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

## Outcome-quality evidence

Recent Supabase BotA M15 outcomes:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
```

March component sample:

```text
BASELINE: 51 rows, 13W/38L, -264.1 pips
ADX<30: 17 rows, 9W/8L, +98.0 pips
SCORE>=70 + ADX<30: 12 rows, 9W/3L, +174.2 pips
```

June-July later-period matched subset:

```text
PUBLISHED=13
MATCHED=9
UNMATCHED=4
MATCH_RATE=69.2%
MATCHED_BASELINE=-70.2 pips
SCORE>=70 + ADX<30=+13.1 pips
SCORE>=70 + ADX<30 + NO_EXTREME=+28.9 pips
ADX>=30 matched rows=0W/4L, -83.3 pips
```

The cross-period direction is consistent with an ADX/late-entry calibration problem, but 69.2% local match coverage is not sufficient to approve a production rule.

## Supabase timestamp warning

Exact `public.signals.created_at` values were independently re-read on 2026-08-07. Several known matched signals have creation timestamps that do not equal local watcher decision timestamps. Treat `created_at` as publication/storage timing unless semantics are proven. Do not use it as the sole join key.

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
- active service path assumed to be repository path;
- oversized terminal packages;
- CSV field-name mismatch;
- 13-column header with 25-column rows;
- direct-main connector fallback violation;
- stale narrow ledger almost mistaken for current performance evidence;
- monotonic score-strength mapping almost mistaken for calibrated entry quality;
- in-sample counterfactual almost mistaken for production validation;
- partial temporal match coverage almost mistaken for out-of-sample proof;
- Supabase publication timestamp almost mistaken for decision timestamp.

## Current prevention rules

- Do not equate more Telegram messages with a repaired trading system.
- Do not lower score/H1/Telegram thresholds before outcome calibration.
- Do not treat stronger ADX or more extreme RSI as automatically better entries.
- Do not derive an exact production threshold from one narrow historical window.
- Do not claim a 7/7 in-sample subset is a 100% strategy.
- Do not call 9/13 later-period matching full out-of-sample validation.
- Freeze candidate rules before later-period testing.
- Resolve missing component rows or record retention gaps explicitly.
- Keep evidence packages small and dated.
- Full-file replacement only for approved mutations.
- Branch -> verified diff -> PR; never direct-main fallback.

## Exactly one next investigation

Resolve the four unmatched June 23-26 published signals by inspecting the nearest retained local alert candidates with relaxed matching. If the component rows are absent, record the retention gap and proceed to a true historical replay using raw candles and the live scoring path.
