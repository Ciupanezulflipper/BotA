# BotA Runtime Error Log

Last updated: 2026-08-07 18:58 UTC

This is the canonical compact error and prevention index. Historical full text remains in Git history, `ERRORS.md`, dated audit records, and GitHub issue/PR history.

Current signal evidence:

- `audits/LOCAL_RETENTION_GAP_2026-08-07.md`
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

## Current status — 2026-08-07

```text
PRODUCTION_VALIDATION=FAILED_HISTORICAL
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_CONTROL_PLANE=DEGRADED_6_OWNED_1_ORPHAN
CURRENT_REQUIRED_RUNNING=7_OF_7
LIVE_WATCHER=RUNNING
LIVE_PAIRS=EURUSD_GBPUSD_ONLY
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
LOCAL_LEDGER_JOINED_COMPONENT_ROWS=51
LOCAL_LEDGER_JOIN_RATE=100_PERCENT
MARCH_TOTAL_PIPS=-264.1
MARCH_ADX_LT30_PIPS=+98.0
MARCH_SCORE70_ADX_LT30_PIPS=+174.2
MARCH_SCORE70_ADX_LT30_WR=75.0_PERCENT
TEMPORAL_MATCHED=9_OF_13
TEMPORAL_MATCH_RATE=69.2_PERCENT
TEMPORAL_MATCHED_BASELINE_PIPS=-70.2
TEMPORAL_ADX_LT30_PIPS=+13.1
TEMPORAL_ADX_LT30_NO_EXTREME_PIPS=+28.9
TEMPORAL_ADX_GTE30=0W_4L_MINUS83.3_PIPS
UNMATCHED_TARGETS=4
UNMATCHED_RELAXED_MATCHES=0
UNMATCHED_RELAXED_COMPONENT_MATCHES=0
LOCAL_RETENTION_GAP=CONFIRMED
STRATEGY_MUTATION_ALLOWED=NO_PENDING_TRUE_REPLAY
```

## Canonical error index

### E001 — Scope branching
Repository, runtime, documentation, deployment, and strategy work were mixed.
Prevention: one phase, evidence domain, and acceptance gate per package.

### E003 — Duplicate execution sources
Cron, runit, boot files, and wrappers could own the same component.
Prevention: prove one execution source for every component.

### E004 — Dead manager with orphaned supervisors
A manager died while child `runsv` processes survived under PID 1.
Prevention: verify manager, parentage, ownership, and restart capability together.

### E007 — Recursive scan entered runit FIFOs
Prevention: whitelist regular files and exclude supervise directories.

### E009 — `pipefail` converted zero matches into abort
Prevention: explicitly tolerate expected zero matches.

### E012 — Deadman stale while services appeared running
Prevention: health must prove monotonic forward progress.

### E015 — Active wall-clock dependencies
Prevention: server UTC for market semantics; monotonic/boottime for cadence and health.

### E017 — Inaccessible `/proc/uptime`
Prevention: never depend on `/proc/uptime` on this device.

### E021 — Continuity lagged runtime truth
Prevention: update canonical docs with explicit UTC date after each material gate.

### E022 — Oversized package burdened Termux
Prevention: bounded, pager-proof packages and small direct proofs.

### E027 — Control-plane regression after prior closure
Prevention: ownership gate before deeper diagnosis.

### E031 — `supervise/pid` misidentified as `runsv`
Prevention: service PID -> PPID -> `runsv` -> manager chain.

### E032 — Manager existed while supervisors were orphans
Prevention: manager existence and service ownership are separate gates.

### E039 — Continuous guard associated with repeated Termux restarts
Prevention: no continuous recovery without executable-path proof, locking, backoff, kill switch, failure injection, and restart observation.

### E040 — D1 mismatch survived broad discovery
Status: CLOSED. `tf_minutes("D1")` now returns 1440 on the phone.

### E043 — Supervisor wrapper contradicted disabled-recovery policy
Status: CLOSED for that wrapper path.

### E045 — Strict shell mode left active in interactive Termux
Prevention: strict mode only inside a bounded child process.

### E046 — Active service path assumed to be repository path
Prevention: compare realpath, mode, and checksum before deployment.

### E047 — Runtime work obscured the signal-throughput acceptance criterion
Recorded: 2026-08-07.

```text
1427 valid BUY/SELL
903 rejected by M15 score gate
410 rejected by H1-neutral veto
4 rejected by H4+D1 opposition
110 strategy-accepted
```

### E048 — Zero-entry symptom almost promoted to root cause
Recorded: 2026-08-07.

```text
zero_entry_buy_sell_rows=0
```

Verdict: zero entry is a HOLD symptom, not the root cause of lost BUY/SELL signals.

### E049 — Ad-hoc CSV audit used the wrong field name
Recorded: 2026-08-07.
Prevention: validate required headers and fail closed.

### E050 — Pager captured a large Git forensic command
Recorded: 2026-08-07.
Prevention: disable pagers and keep output bounded.

### E051 — Legacy alerts header with newer 25-column rows
Recorded: 2026-08-07.
Prevention: explicit schema/version migration or a versioned decision ledger.

### E052 — Documentation connector direct-main process violation
Recorded: 2026-08-07.
Prevention: always create/verify branch before write; never use `main` as fallback.

### E053 — Strategy and Telegram use different score floors
Recorded: 2026-08-07.

```text
FILTER_SCORE_MIN_ALL=65
TELEGRAM_MIN_SCORE=70
```

Historical delivered `<70` evidence is poor, so lowering the Telegram floor is not supported.

### E054 — Thirty-minute Telegram cooldown suppresses accepted events
Recorded: 2026-08-07.

```text
TELEGRAM_COOLDOWN_SECONDS=1800
TELEGRAM_COOLDOWN_EVENTS=38_OF_106_MATCHED_ACCEPTED
```

### E055 — Live pair universe contains only two pairs
Recorded: 2026-08-07.

```text
PAIRS=EURUSD GBPUSD
TIMEFRAMES=M15
```

### E056 — Accepted CSV count exceeds matched retained delivery-log count
Recorded: 2026-08-07.

```text
CSV_ACCEPTED_BUY_SELL_TOTAL=110
MATCHED_ACCEPTED_LOG_EVENTS=106
UNMATCHED_ACCEPTED_ROWS=4
```

### E057 — Cooldown non-equality almost promoted to proof of new trades
Recorded: 2026-08-07 17:54 UTC.

```text
COOLDOWN_TOTAL=38
EXACT_DUPLICATE=0
NOT_EXACT_DUPLICATE=38
DIRECTION_CHANGED=0
```

All 38 remained the same direction as the preceding sent event.

### E058 — Recent high scores do not imply recent positive edge
Recorded: 2026-08-07.

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
75-84_TOTAL_PIPS=-36.40
85+_TOTAL_PIPS=-35.00
```

### E059 — Local signal ledger is stale and narrow
Recorded: 2026-08-07 18:09 UTC.

```text
LEDGER_ROWS=51
WIN=13
LOSS=38
FIRST=2026-03-09T21:45:07+02:00
LAST=2026-03-10T15:15:07+02:00
```

Prevention: always report first/last timestamps and coverage span before using a local outcome ledger.

### E060 — Score magnitude is inversely calibrated in the March component sample
Recorded: 2026-08-07 18:15 UTC.

```text
<70:   WR=18.2% PIPS=-83.5
70-74: WR=50.0% PIPS=+2.1
75-84: WR=31.6% PIPS=-44.8
85+:   WR=17.6% PIPS=-137.9
```

Prevention: never assume a higher handcrafted score is better until score buckets are calibrated against realized outcomes.

### E061 — ADX reward appears directionally wrong in the March sample
Recorded: 2026-08-07 18:15 UTC.

```text
ADX_20_29: n=17 WR=52.9% PIPS=+98.0
ADX_30_39: n=26 WR=7.7% PIPS=-319.1
ADX_40_PLUS: n=8 WR=25.0% PIPS=-43.0
```

Current scoring awards maximum ADX contribution for ADX >=30. Prevention: treat trend-strength scoring as potentially non-linear and validate against realized outcomes.

### E062 — RSI extremity reward conflicts with March outcomes
Recorded: 2026-08-07 18:15 UTC.

```text
RSI_EXTREME: n=18 WR=11.1% PIPS=-229.2
RSI_STRETCHED: n=11 WR=45.5% PIPS=+69.4
RSI_MODERATE: n=22 WR=27.3% PIPS=-104.3
```

Prevention: separate momentum strength from entry quality; do not monotonically reward overextension without outcome calibration.

### E063 — In-sample counterfactual can look perfect without proving edge
Recorded: 2026-08-07 18:38 UTC.

```text
BASELINE: N=51 W=13 L=38 WR=25.5% PIPS=-264.1
ADX<30: N=17 W=9 L=8 WR=52.9% PIPS=+98.0
SCORE>=70 + ADX<30: N=12 W=9 L=3 WR=75.0% PIPS=+174.2
SCORE>=70 + ADX<30 + NO_EXTREME: N=7 W=7 L=0 WR=100.0% PIPS=+171.0
```

The 7/7 subset is not production validation. Prevention: freeze candidate rules and validate on a separate unseen historical period before mutation.

### E064 — ADX 30-39 failure persists across RSI states in March sample
Recorded: 2026-08-07 18:38 UTC.

```text
30-39/MODERATE: n=8 W=0 L=8 PIPS=-122.4
30-39/STRETCHED: n=8 W=2 L=6 PIPS=-14.4
30-39/EXTREME: n=10 W=0 L=10 PIPS=-182.3
```

This strengthens the directional ADX concern but still does not establish a final production threshold.

### E065 — Later-period ADX cross-check supports the same direction but coverage is incomplete
Recorded: 2026-08-07 18:46 UTC.

```text
PUBLISHED=13
MATCHED=9
UNMATCHED=4
MATCH_RATE=69.2%
MATCHED_BASELINE: N=9 W=2 L=7 PIPS=-70.2
SCORE>=70 + ADX<30: N=5 W=2 L=3 PIPS=+13.1
SCORE>=70 + ADX<30 + NO_EXTREME: N=4 W=2 L=2 PIPS=+28.9
ADX_30_39: N=3 W=0 L=3 PIPS=-57.4
ADX_40_PLUS: N=1 W=0 L=1 PIPS=-25.9
```

All four matched ADX >=30 rows lost, totaling -83.3 pips. Prevention: resolve unmatched component rows or record the retention gap before claiming out-of-sample validation.

### E066 — Supabase `created_at` is not proven to equal BotA decision time
Recorded: 2026-08-07.

Several already-matched signals have `created_at` values that do not equal local watcher decision timestamps.

Prevention: treat Supabase `created_at` as publication/storage timing until its semantics are proven; never use it as the sole join key.

### E067 — Local retention gap blocks full June-July component reconstruction
Recorded: 2026-08-07 18:58 UTC.

```text
TARGETS_TOTAL=4
TARGETS_WITH_NEARBY_ROWS=1
TARGETS_WITH_RELAXED_MATCH=0
TARGETS_WITH_RELAXED_COMPONENT_MATCH=0
VERDICT=LOCAL_RETENTION_GAP_CONFIRMED
```

Three unmatched published targets had no same-pair/same-direction M15 rows within +/-2 days. The fourth had nearby rows but no plausible identity match.

Prevention: once a retention gap is proven, stop widening heuristic match tolerances. Use raw historical candles and the live scoring path for true replay.

## Current exact funnel

Strategy:

```text
SCORE_GATE=903
H1_NEUTRAL=410
H4_D1_OPPOSE=4
TOTAL_REJECTED_VALID_BUY_SELL=1317
```

Delivery:

```text
TELEGRAM_SENT=61
TELEGRAM_COOLDOWN=38
TELEGRAM_SCORE_GATE=6
TELEGRAM_FAILED=1
```

Recent outcome quality:

```text
13 BotA M15 signals since 2026-06-01
3 wins
9 losses
1 cancelled
-71.40 pips
```

Cross-period ADX evidence:

```text
March baseline=-264.1 pips
March ADX<30=+98.0 pips
June-July matched baseline=-70.2 pips
June-July matched ADX<30=+13.1 pips
June-July matched ADX>=30=0W/4L, -83.3 pips
```

## Efficient protocol

1. Read dated current handoff/audits first.
2. One narrow evidence question per package.
3. Small pager-proof commands only.
4. Validate schemas and time coverage before field analysis.
5. Separate runtime, strategy, delivery, and realized outcomes.
6. Preserve phone state before mutation.
7. Full-file replacement for approved mutation.
8. Date every material finding in UTC.
9. Branch -> verified diff -> PR; never direct-main fallback.
10. Freeze candidate rules before out-of-sample testing.
11. Resolve unmatched records before claiming temporal validation.
12. Stop heuristic reconstruction after a confirmed retention gap.

## Exactly one next action

Run a true historical replay from raw candles through the live production scoring/fusion semantics with frozen policies A/B/C. Compare signal count, wins/losses, total pips, and preferably MAE/MFE. No production strategy mutation until this validation is complete.
