# BotA Errors and Silent-Failure Register

Last updated: 2026-08-07 18:38 UTC

Purpose: preserve verified failure classes, current open risks, and prevention rules without repeating broad audits.

Current signal evidence:

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
MARCH_SCORE70_ADX_LT30_PIPS=+174.2
MARCH_SCORE70_ADX_LT30_WR=75.0_PERCENT
STRATEGY_MUTATION_ALLOWED=NO_PENDING_OUT_OF_SAMPLE_REPLAY
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

## March component calibration finding

The 51-row local March ledger joined 100% to extended alert components:

```text
JOINED=51
UNMATCHED=0
WINS=13
LOSSES=38
TOTAL_PIPS=-264.1
```

Key component evidence:

```text
ADX 20-29: n=17 WR=52.9% PIPS=+98.0
ADX 30-39: n=26 WR=7.7% PIPS=-319.1
ADX 40+:   n=8  WR=25.0% PIPS=-43.0
RSI EXTREME: n=18 WR=11.1% PIPS=-229.2
RSI STRETCHED: n=11 WR=45.5% PIPS=+69.4
score 85+: n=17 WR=17.6% PIPS=-137.9
```

## Counterfactual finding — 2026-08-07 18:38 UTC

```text
BASELINE: N=51 W=13 L=38 WR=25.5% PIPS=-264.1
SCORE>=70: N=40 W=11 L=29 WR=27.5% PIPS=-180.6
NO_EXTREME_RSI: N=33 W=11 L=22 WR=33.3% PIPS=-34.9
ADX<30: N=17 W=9 L=8 WR=52.9% PIPS=+98.0
ADX<30 + NO_EXTREME: N=12 W=7 L=5 WR=58.3% PIPS=+94.8
SCORE>=70 + ADX<30: N=12 W=9 L=3 WR=75.0% PIPS=+174.2
SCORE>=70 + ADX<30 + NO_EXTREME: N=7 W=7 L=0 WR=100.0% PIPS=+171.0
```

The 7/7 result is high overfit risk because the same narrow sample was used to discover and evaluate it. It must not be promoted to production.

The broader evidence is stronger: `ADX<30` alone retains 17 trades and changes the sample from -264.1 to +98.0 pips. ADX 30-39 is poor across RSI states. Removing extreme RSI helps but is insufficient by itself.

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
- monotonic score-strength mapping almost mistaken for calibrated entry quality;
- in-sample counterfactual almost mistaken for production validation.

## Current prevention rules

- Do not equate more Telegram messages with a repaired trading system.
- Do not lower score/H1/Telegram thresholds before outcome calibration.
- Do not treat stronger ADX or more extreme RSI as automatically better entries.
- Do not derive an exact production threshold from one narrow historical window.
- Do not claim a 7/7 in-sample subset is a 100% strategy.
- Freeze candidate rules before out-of-sample validation.
- Keep March local-ledger evidence separate from recent June-August Supabase outcomes.
- Keep evidence packages small and dated.
- Full-file replacement only for approved mutations.
- Branch -> verified diff -> PR; never direct-main fallback.

## Exactly one next investigation

Run an out-of-sample replay over a separate historical period, with candidate policies fixed before viewing outcomes:

```text
A: current production baseline
B: score >=70 AND ADX <30
C: score >=70 AND ADX <30 AND no extreme RSI
```

Compare retained signal count, win/loss, total pips, and preferably MAE/MFE. No production strategy mutation until this validation is complete.
