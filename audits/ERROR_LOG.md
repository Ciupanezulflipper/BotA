# BotA Runtime Error Log

Last updated: 2026-08-07 18:46 UTC

This is the canonical compact error and prevention index. Historical full text remains in Git history, `ERRORS.md`, dated audit records, and GitHub issue/PR history.

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

## Canonical error index

### E001 — Scope branching
Repository, runtime, documentation, deployment, and strategy work were mixed. Prevention: one phase and acceptance gate per package.

### E003 — Duplicate execution sources
Cron, runit, boot files, and wrappers could own the same component. Prevention: prove one execution source for every component.

### E004 — Dead manager with orphaned supervisors
A manager died while child `runsv` processes survived under PID 1. Prevention: verify manager, parentage, ownership, and restart capability together.

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
Status: CLOSED. `tf_minutes("D1")` returns 1440 on the phone.

### E043 — Supervisor wrapper contradicted disabled-recovery policy
Status: CLOSED for that wrapper path.

### E045 — Strict shell mode left active in interactive Termux
Prevention: strict mode only inside a bounded child process.

### E046 — Active service path assumed to be repository path
Prevention: compare realpath, mode, and checksum before deployment.

### E047 — Runtime work obscured signal-throughput acceptance
Recorded: 2026-08-07. 1427 valid BUY/SELL -> 903 score rejects -> 410 H1-neutral rejects -> 4 H4+D1 rejects -> 110 accepted.

### E048 — Zero-entry symptom almost promoted to root cause
Recorded: 2026-08-07. `zero_entry_buy_sell_rows=0`. Zero entry is a HOLD symptom.

### E049 — Ad-hoc CSV audit used the wrong field name
Recorded: 2026-08-07. Prevention: validate required headers and fail closed.

### E050 — Pager captured a large Git forensic command
Recorded: 2026-08-07. Prevention: disable pagers and keep output bounded.

### E051 — Legacy alerts header with newer 25-column rows
Recorded: 2026-08-07. Prevention: explicit schema/version migration or a versioned decision ledger.

### E052 — Documentation connector direct-main process violation
Recorded: 2026-08-07. Prevention: always create/verify branch before write; never use `main` as fallback.

### E053 — Strategy and Telegram use different score floors
Recorded: 2026-08-07. `FILTER_SCORE_MIN_ALL=65`, `TELEGRAM_MIN_SCORE=70`. Historical delivered `<70` evidence is poor, so lowering Telegram is not supported.

### E054 — Thirty-minute Telegram cooldown suppresses accepted events
Recorded: 2026-08-07. `38/106` matched accepted events were cooldown-suppressed.

### E055 — Live pair universe contains only two pairs
Recorded: 2026-08-07. `PAIRS=EURUSD GBPUSD`.

### E056 — Accepted CSV count exceeds retained matched delivery count
Recorded: 2026-08-07. 110 accepted CSV rows vs 106 retained matched log events; four delivery outcomes remain unknown.

### E057 — Cooldown non-equality almost promoted to proof of new trades
Recorded: 2026-08-07 17:54 UTC. All 38 cooldown rows remained the same direction as the preceding sent event.

### E058 — Recent high scores do not imply recent positive edge
Recorded: 2026-08-07. 13 recent BotA M15 outcomes = 3W/9L/1C, -71.40 pips.

### E059 — Local signal ledger is stale and narrow
Recorded: 2026-08-07 18:09 UTC. 51 rows from 2026-03-09 through 2026-03-10 only.

### E060 — Score magnitude is not calibrated in the March component sample
Recorded: 2026-08-07 18:15 UTC. `85+` = 17.6% WR, -137.9 pips.

### E061 — ADX reward appears directionally wrong in the March sample
Recorded: 2026-08-07 18:15 UTC. ADX 20-29 = +98.0 pips; ADX 30-39 = -319.1 pips.

### E062 — RSI extremity reward conflicts with March outcomes
Recorded: 2026-08-07 18:15 UTC. Extreme RSI = -229.2 pips; stretched RSI = +69.4 pips.

### E063 — In-sample counterfactual can look perfect without proving edge
Recorded: 2026-08-07 18:38 UTC. A 7/7 subset was discovered and evaluated on the same data; it is not production validation.

### E064 — ADX 30-39 failure persists across RSI states in March sample
Recorded: 2026-08-07 18:38 UTC. The 30-39 band was poor in moderate, stretched, and extreme RSI subgroups.

### E065 — Later-period ADX cross-check is directionally positive but incomplete
Recorded: 2026-08-07 18:46 UTC.

```text
PUBLISHED=13
MATCHED=9
MATCH_RATE=69.2%
MATCHED_BASELINE: 2W/7L, -70.2 pips
SCORE>=70 + ADX<30: 2W/3L, +13.1 pips
SCORE>=70 + ADX<30 + NO_EXTREME: 2W/2L, +28.9 pips
ADX>=30 matched rows: 0W/4L, -83.3 pips
```

Interpretation: this later subset supports the March ADX concern but does not satisfy full out-of-sample validation because four published signals lack matched retained local component rows.

Prevention: do not approve a production threshold from partial later-period coverage.

### E066 — Supabase `created_at` is not proven to be BotA decision time
Recorded: 2026-08-07.

Exact read-only Supabase rows were re-queried. Several signals already matched by pair/entry/score have `created_at` timestamps that do not equal the local watcher decision timestamps.

Prevention: treat Supabase `created_at` as publication/storage timing until semantics are proven; never use it as the sole signal join key.

## Current exact evidence

Strategy funnel:

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
10. Freeze candidate rules before later-period testing.
11. Resolve unmatched records before claiming out-of-sample validation.

## Exactly one next action

Resolve the four unmatched June 23-26 published signals against retained local alerts with relaxed matching. If the rows are absent, record the retention gap and proceed to a true historical replay using raw candles and the live scoring path. No production strategy mutation until then.
