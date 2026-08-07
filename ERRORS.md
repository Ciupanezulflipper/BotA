# BotA Errors and Silent-Failure Register

Last updated: 2026-08-07 18:15 UTC

Purpose: preserve verified failure classes, current open risks, and prevention rules without repeating broad audits.

Current signal evidence:

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
MARCH_ADX_20_29_PIPS=+98.0
MARCH_ADX_30_39_PIPS=-319.1
MARCH_RSI_EXTREME_PIPS=-229.2
MARCH_RSI_STRETCHED_PIPS=+69.4
MARCH_SCORE_85PLUS_PIPS=-137.9
STRATEGY_MUTATION_ALLOWED=NO_PENDING_COUNTERFACTUAL_AUDIT
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

## Recent outcome quality risk

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

Recent high scores are not showing reliable calibration.

## March component calibration finding — 2026-08-07 18:15 UTC

The 51-row local March ledger joined 100% to extended alert components:

```text
JOINED=51
UNMATCHED=0
WINS=13
LOSSES=38
TOTAL_PIPS=-264.1
```

Score outcome:

```text
<70:   WR=18.2% PIPS=-83.5
70-74: WR=50.0% PIPS=+2.1
75-84: WR=31.6% PIPS=-44.8
85+:   WR=17.6% PIPS=-137.9
```

The highest score bucket was the worst-performing bucket.

RSI entry-state outcome:

```text
EXTREME:   n=18 WR=11.1% PIPS=-229.2
STRETCHED: n=11 WR=45.5% PIPS=+69.4
MODERATE:  n=22 WR=27.3% PIPS=-104.3
```

ADX outcome:

```text
20-29: n=17 WR=52.9% PIPS=+98.0
30-39: n=26 WR=7.7%  PIPS=-319.1
40+:   n=8  WR=25.0% PIPS=-43.0
```

Current code awards maximum ADX contribution at ADX >=30. In this March sample, that mapping is directionally opposite to realized outcome quality. Current RSI scoring also rewards greater distance from 50 while the extreme group was dramatically worse than the intermediate stretched group.

The working diagnosis is now that the score over-rewards trend intensity and under-prices late-entry/exhaustion risk.

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
- stale narrow ledger almost mistaken for current performance evidence;
- monotonic score-strength mapping almost mistaken for calibrated entry quality.

## Current prevention rules

- Do not equate more Telegram messages with a repaired trading system.
- Do not lower score/H1/Telegram thresholds before outcome calibration.
- Do not treat stronger ADX or more extreme RSI as automatically better entries.
- Do not derive an exact production threshold from one narrow historical window.
- Keep March local-ledger evidence separate from recent June-August Supabase outcomes.
- Keep evidence packages small and dated.
- Full-file replacement only for approved mutations.
- Branch -> verified diff -> PR; never direct-main fallback.

## Exactly one next investigation

Run a read-only counterfactual using the 51 joined March rows and the recent component-matched published outcomes. Compare simple ADX/RSI candidate corrections and report retained signal count, win rate, and pips before any production strategy mutation.
