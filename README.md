# BotA — Forex Signal Bot

BotA is a Forex signal system currently running on Android/Termux.

## Current status

```text
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
SIGNAL_GENERATION=PROVEN
TELEGRAM_DELIVERY=PROVEN
MARKET_SCANNING=PROVEN
CURRENT_RUNIT_CONTROL_PLANE=UNSTABLE
CURRENT_ARCHITECTURE_DECISION=REPLACE_RUNTIME_ORCHESTRATION_PRESERVE_TRADING_ENGINE
STRATEGY_THRESHOLDS=FROZEN
CLOUD_MIGRATION=DEFERRED_UNTIL_STRATEGY_PROVES_ITSELF
PRODUCTION_TRADING_READY=NO
```

The trading engine has demonstrated that it can scan markets, produce actionable decisions, and deliver Telegram signals. The unresolved problem is runtime/control-plane persistence on Android/Termux.

Do not infer current production state from old backtests, `BOTLOG.md`, `BOOTLOG.md`, historical continuity entries, or an Android working-tree HEAD.

## Architecture decision — 10 August 2026

After repeated HEALTHY → DEGRADED → RECOVERY oscillation and a multi-model forensic review, the current `termux-services` / `runit` / `runsvdir` orchestration layer is no longer the target architecture.

The decision is:

```text
PRESERVE=TRADING_ENGINE
REPLACE=RUNIT_RUNSVDIR_MULTI_AUTHORITY_ORCHESTRATION
TARGET_RUNTIME=CONSOLIDATED_BOTA_RUNTIME
TARGET_EXTERNAL_GUARD=SMALL_INDEPENDENT_PROGRESS_MONITOR_RESTARTER
KEEP_STRATEGY_UNCHANGED=YES
KEEP_THRESHOLDS_UNCHANGED=YES
```

This is an orchestration decision, not a strategy rewrite.

### Why this decision was made

The current runtime has repeatedly demonstrated the following sequence:

```text
HEALTHY
  -> runsvdir manager disappears
  -> one or more runsv children survive and are reparented to PID 1
  -> another manager later appears
  -> ownership becomes partial or split
  -> sv commands can fail or time out
  -> watchdog recovery eventually restores health
  -> degradation returns later
```

A correct topology has also been proven temporarily, including a 31-sample / five-minute persistence gate with one manager, seven owned services, seven running services, zero orphans, and zero duplicates. Therefore the system can form a healthy topology; the unresolved defect is persistence and recovery ownership over time.

The explicit launcher `SVDIR` repair was valid and necessary, but later degradation proved it was not sufficient.

`crond` is treated primarily as a victim of manager/control-plane failure. The separate bare-crond fallback is also considered an ownership hazard and must not exist in the replacement runtime.

### Control-authority finding

The Android deployment accumulated multiple possible lifecycle authorities, including profile startup, Termux:Boot, duplicate boot invocation, a periodic cron watchdog guard, the native watchdog, `service-daemon`, and the separate `start-crond` fallback.

The watchdog flock protects watchdog-instance uniqueness only; it does not establish a global lifecycle authority across all of those mechanisms.

The replacement must therefore have one clear runtime owner and one deliberately simple external restarter/monitor. Opening a shell must never alter production runtime topology.

## Replacement-runtime requirements

The replacement is **not** approved as a naive "one Python PID means healthy" design.

The consolidated runtime must preserve existing trading behavior while satisfying these requirements:

1. **Useful-progress health, not PID health.** Durable timestamps must prove that real work completed, such as market-data/update work, scan cycles, closer/outcome work, trusted-clock validation, and outbound delivery processing where applicable.
2. **Independent minimal restarter.** A tiny external process or wrapper may restart a dead or stale runtime, but it must not become another competing orchestration system.
3. **Single-instance ownership.** One lock/lease must prevent duplicate runtime instances.
4. **Bounded I/O.** Network and subprocess operations must have explicit timeouts so one blocked operation cannot silently freeze all BotA work.
5. **Crash-consistent state.** Signals, outcome updates, delivery state, and other side effects must use durable identifiers/state so a restart cannot silently duplicate or lose actions.
6. **Fail closed on stale clock/data/state.** No signal should be emitted from stale or ambiguous runtime state.
7. **Restart reconciliation.** Startup must verify durable state before resuming work.
8. **No strategy changes during migration.** Pair scope, M15 execution scope, signal thresholds, filters, and policy behavior remain frozen unless a separate strategy-analysis decision is made later.

## Legacy death-provenance evidence

Before the old runit layer is removed, capture one real `runsvdir` termination if practical without delaying replacement development.

The desired evidence is the manager's actual termination class:

```text
SIGKILL / Android or resource pressure
SIGTERM / explicit local termination
normal or nonzero process exit
clean HUP-style shutdown
```

This evidence is useful because Android process pressure that killed `runsvdir` could also threaten a consolidated Python runtime. It is an evidence task, not permission to resume the old repair cycle.

## Strategy proof gate

BotA must prove that the strategy deserves permanent hosting before paid cloud migration.

The current business gate is **at least 60% closed-trade win rate**, but win rate alone is not sufficient. Evaluation must also include positive expectancy and costs/spread, with a meaningful clean sample of closed outcomes.

Minimum evidence requirements before declaring the strategy proven:

```text
WIN_RATE_TARGET=>=60_PERCENT
EXPECTANCY=>0
PROFIT_FACTOR=>1
OUTCOME_SAMPLE=MEANINGFUL_AND_CLEAN
UNKNOWN_OUTCOMES=0_FOR_EVALUATED_SAMPLE
DUPLICATE_SIGNALS=0
MISSING_REQUIRED_CLOSES=0
TRADING_COSTS_INCLUDED=YES
```

Do not lower thresholds or force signals to manufacture a passing result.

Until this gate is met, the primary objective is to make BotA a reliable evidence-producing system in shadow/paper operation rather than spend additional money on permanent infrastructure.

## Cloud decision

A Linux cloud/VPS runtime is the preferred long-term production location **after** the strategy proof gate is satisfied.

Cloud migration is intentionally deferred for now so infrastructure cost is not used to host an unproven strategy. Android may continue to be used during the proof phase, but the replacement runtime must be designed so it can later move to standard Linux with minimal trading-engine changes.

## Start here

For every new engineering/audit session, read in this order:

1. `README.md` — current architecture decision and strategy proof gate.
2. `AI_START_HERE.md` — current operating rules and status.
3. `CONTINUITY_CURRENT.md` — current production handoff and next action.
4. `CHAT_HANDOFF_BOTA.md` — compact cross-chat handoff.
5. `state/STATE.json` — machine-readable repository handoff snapshot.
6. `DECISIONS.md` — previously locked decisions; entries conflicting with this README's 10 August 2026 runtime decision must be treated as superseded until reconciled.
7. `ERRORS.md` and `audits/ERROR_LOG.md` — historical failure classes, fixes, and prevention rules.

Older dated audits, `BOTLOG.md`, `BOOTLOG.md`, and `CONTINUITY.md` remain historical evidence. They do not override the runtime architecture decision above.

## Immediate engineering objective

```text
1_FREEZE_TRADING_STRATEGY
2_CAPTURE_LEGACY_MANAGER_DEATH_PROVENANCE_IF_AVAILABLE
3_BUILD_CONSOLIDATED_EVIDENCE_RUNTIME
4_ADD_WORK_DERIVED_LIVENESS_AND_MINIMAL_EXTERNAL_RESTARTER
5_RUN_SHADOW_PAPER_MODE
6_COLLECT_CLEAN_CLOSED_OUTCOMES
7_EVALUATE_WIN_RATE_EXPECTANCY_PROFIT_FACTOR
8_IF_STRATEGY_PASSES_THEN_MOVE_TO_LINUX_CLOUD
```

Do not restart the historical runit repair loop unless new evidence proves that preserving the old orchestration is materially safer than the replacement architecture.
