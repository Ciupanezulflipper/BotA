# BotA Replacement Runtime — Six-Model Architecture Audit

Date: **2026-08-10 UTC**
Status: **ARCHITECTURE AUDIT COMPLETE**
Scope: runtime/orchestration only; trading strategy and thresholds frozen.

## Purpose

This document records the final six-model architecture review performed after the BotA `runit` / `runsvdir` control-plane incident. The purpose was not to re-audit the trading strategy. The purpose was to choose the smallest credible replacement runtime that can reliably collect trustworthy live signal/outcome evidence on Android/Termux before any paid cloud migration.

The six reviews were supplied by:

1. Claude
2. Kimi
3. DeepSeek
4. Grok
5. Gemini
6. Perplexity

The raw reviews differed on implementation details, but all were evaluated against the same constraints:

- preserve the proven trading engine;
- stop spending engineering time on runit/runsvdir ownership churn;
- keep cloud spending deferred until BotA proves economic value;
- distinguish PID/process liveness from actual useful-work progress;
- prevent duplicate signals and state loss across hard kills/restarts;
- treat Android suspend/Doze/LMK behavior as a first-class failure input;
- require strict parity, fault-injection, restart, Android, and shadow-live acceptance gates before cutover.

## Proven facts entering the audit

The following facts were treated as established input:

```text
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAME=M15
SIGNAL_GENERATION=PROVEN
TELEGRAM_DELIVERY=PROVEN
MARKET_SCANNING=PROVEN
TRADING_ENGINE_REWRITE_REQUIRED=NO
CURRENT_RUNIT_CONTROL_PLANE=UNSTABLE
```

Observed failure class:

```text
healthy runsvdir topology
-> old runsvdir disappears
-> one or more runsv children survive
-> surviving runsv become PPID 1
-> another runsvdir appears
-> ownership becomes partial/split
-> rc=111/timeouts/duplicate-manager recovery churn
-> temporary recovery
-> degradation returns
```

A real production signal had also been generated and delivered:

```text
USDJPY M15 BUY
score=81.60
entry=159.16400
SL=159.01418
TP=159.46365
```

Recent production proof also showed:

```text
scans=150
actionable_buy_sell=32
hold_no_trade=118
telegram_eligible=2
```

## Audit 1 — Claude

### Decision

**Option A:** one Python orchestrator plus one minimal externally-triggered restarter, while executing existing trading scripts as subprocesses instead of refactoring the engine.

### Main reasoning

Claude rejected a naive all-in-one Python process because it can replace a loud topology failure with a silent living-zombie failure. It emphasized that useful-work liveness must be derived from completed watcher/closer/clock work, not heartbeat/PID existence.

It also argued that Termux:Boot alone is insufficient for mid-session runtime death and that a second minimal resurrection mechanism is necessary. It recommended a crash-only discipline: if progress stalls, fail hard and let the external owner restart the runtime rather than trying to self-heal in-process.

### Critical requirements raised

- durable `last_successful_scan_utc` / work-derived progress timestamps;
- one dumb restarter outside the runtime;
- hard network/subprocess timeouts;
- crash-consistent side effects;
- per-cycle clock validation;
- build migration now but treat legacy death-signal capture as useful before final cutover;
- run the replacement in shadow before production cutover.

### Final position

```text
ARCHITECTURE=OPTION_A
PERSISTENT_PROCESSES=2
TRADING_ENGINE_INTEGRATION=EXEC_EXISTING_MODULES_AS_SUBPROCESSES
RUNSVDIR_DEATH_SIGNAL=USEFUL_BUT_NOT_REQUIRED_FOR_BUILD
```

## Audit 2 — Kimi

### Decision

**Option A:** two persistent processes — a minimal restarter and runtime.

### Main reasoning

Kimi considered the current runit topology a proven failure amplifier. It strongly favored reducing the standing process count and eliminating `cron`, `runit`, `runsvdir`, profile-triggered startup, and bare-crond fallback ownership.

It defined a precise progress heartbeat and required the restarter to kill and restart a living-zombie runtime when progress became stale.

### Important concerns

Kimi identified five key risks for the replacement:

1. restarter dies independently;
2. runtime deadlock/event-loop corruption;
3. crash-time persistent-state corruption;
4. transient subprocess orphan accumulation;
5. Termux:Boot non-execution after reboot.

It recommended atomic writes, bounded subprocess lifetimes, runtime locks, and strict Android acceptance tests.

### Final position

```text
ARCHITECTURE=OPTION_A
PERSISTENT_PROCESSES=2
CRON=REMOVE_COMPLETELY
RUNIT=REMOVE_COMPLETELY
RUNSVDIR_DEATH_SIGNAL=USEFUL_BUT_NOT_REQUIRED
CLOUD_NOW=NO
CLOUD_AFTER_STRATEGY_PROOF=YES
```

## Audit 3 — DeepSeek

### Decision

**Option C:** one persistent shell supervisor that sequentially invokes the existing engine scripts as subprocesses.

### Main reasoning

DeepSeek prioritized fresh-process hygiene and minimal long-lived state. It argued that a shell supervisor avoids Python event-loop deadlocks, memory accumulation, stale connection pools, and GIL/thread failure classes.

It deliberately accepted a major availability gap: if Android kills the supervisor, there is no automatic resurrection until reboot/manual restart. DeepSeek preferred this to reintroducing multiple restart authorities.

### Valuable contributions retained even though Option C was not selected

- keep existing engine scripts unchanged for parity;
- use hard external subprocess timeouts with SIGKILL escalation;
- do not replay stale/missed market scans after Android suspend;
- write intent before side effects and reconcile unknown outcomes on restart;
- fail closed on untrusted clock, stale market data, or inability to persist state;
- require a long Android shadow run.

### Final position

```text
ARCHITECTURE=OPTION_C
PERSISTENT_PROCESSES=1
AUTO_RESURRECTION_AFTER_ANDROID_KILL=NO
TRADING_ENGINE_INTEGRATION=EXEC_EXISTING_MODULES_AS_SUBPROCESSES
```

### Why it was not chosen

The lack of automatic recovery after supervisor death conflicts with the primary operational objective: unattended evidence collection. The replacement must not require a daily reboot/manual intervention merely to restore availability.

## Audit 4 — Grok

### Result

Grok did not provide an independent detailed implementation choice in the supplied response. It correctly identified the assignment as the final architecture-gate document and summarized its purpose: choose the replacement runtime, preserve engine behavior, minimize control-plane risk, and define strict acceptance gates before cutover.

### Contribution to final synthesis

Its response reinforced that architecture selection and acceptance criteria were now the task, not another runit root-cause audit.

## Audit 5 — Gemini

### Decision

**Option A:** a small external shell restarter plus Python orchestrator executing existing modules as subprocesses.

### Main reasoning

Gemini explicitly rejected a fully imported/refactored Python engine for now. Its preferred architecture keeps the long-lived Python orchestrator lightweight and pushes pandas/heavy processing into short-lived child processes, which release memory when they exit.

It favored simple Python thread/subprocess orchestration over asyncio for compatibility with the current shell/Python CLI engine entrypoints.

### Critical requirements raised

- one resurrection authority;
- strict `subprocess` deadlines;
- progress-derived zombie detection;
- hard runtime exit and external restart on useful-work staleness;
- persistent intent/confirmation journal for Telegram and other side effects;
- stale-data rejection after Doze/resume;
- periodic planned restart only if justified by soak data;
- no runit or cron restart path.

### Final position

```text
ARCHITECTURE=OPTION_A
TRADING_ENGINE_INTEGRATION=EXEC_EXISTING_MODULES_AS_SUBPROCESSES
RUNIT=REMOVE_COMPLETELY
CRON=REMOVE_COMPLETELY
CLOUD_NOW=NO
CLOUD_AFTER_STRATEGY_PROOF=YES
FINAL=GO_BUILD
```

## Audit 6 — Perplexity

### Decision

**Option B:** three persistent processes — owner/restarter, trading worker, monitor/progress worker.

### Main reasoning

Perplexity prioritized independent living-zombie detection. It argued that a separate monitor process reduces the blast radius of a deadlocked trading worker and avoids asking one process to prove its own health.

It also strongly required crash-consistency journaling, exact useful-progress fields, strict network deadlines, Android suspend handling, one resurrection authority, and removal of runit/cron/profile startup paths.

### Valuable contributions retained

- explicit required progress fields;
- exact living-zombie definitions tied to market-open conditions and open-signal state;
- durable intent journal with `prepared` / `unknown_outcome` reconciliation;
- fail-closed behavior if closer or trusted clock fails;
- 7–14 day shadow-live gate;
- 100+ closed signals for initial strategy evidence and preferably 200+ for stronger conclusions.

### Why full Option B was not chosen

A dedicated third persistent monitoring process increases Android process exposure and coordination complexity. Its core safety objective can be achieved with the external owner/restarter directly reading durable useful-progress state written by the Python orchestrator. This preserves independent detection without requiring a separate monitor worker.

## Cross-audit agreement

Despite different preferred implementations, the reviews converged on the following points:

```text
PRESERVE_TRADING_ENGINE=YES
REPLACE_RUNIT_RUNSVDIR=YES
MULTIPLE_RESURRECTION_AUTHORITIES=FORBIDDEN
PID_EXISTS_IS_NOT_HEALTH=YES
USEFUL_WORK_PROGRESS_REQUIRED=YES
NETWORK_AND_SUBPROCESS_TIMEOUTS_REQUIRED=YES
CRASH_CONSISTENT_SIDE_EFFECTS_REQUIRED=YES
STALE_CLOCK_OR_DATA_FAIL_CLOSED=YES
ANDROID_DOZE_SUSPEND_MUST_BE_EXPLICITLY_HANDLED=YES
CLOUD_NOW=NO
CLOUD_LATER_IF_STRATEGY_PROVES_ITSELF=YES
```

## Final architecture decision

The selected design is a constrained **Option A** that deliberately absorbs the strongest objections raised against naive single-process designs.

```text
PERSISTENT_PROCESS_1=minimal owner/restarter
PERSISTENT_PROCESS_2=lightweight Python orchestrator
TRANSIENT_PROCESSES=existing BotA engine scripts only while work is running
```

The Python orchestrator is **not** the trading engine rewrite. It schedules and bounds the existing proven engine entrypoints.

### Final integration model

```text
TRADING_ENGINE_INTEGRATION=EXEC_EXISTING_MODULES_AS_SUBPROCESSES
IMPORT_AND_REFACTOR=NO_DURING_MIGRATION
```

The following engine paths remain behavior-frozen during the runtime migration:

```text
tools/data_fetch_candles.sh
tools/indicators_updater.sh
tools/build_indicators.py
tools/scoring_engine.sh
tools/quality_filter.py
tools/m15_h1_fusion.sh
tools/production_signal_policy.py
tools/signal_watcher_pro.sh
tools/watcher_gated_cycle.sh
tools/run_signal_watcher_with_ledger.sh
tools/pipeline_ledger.py
tools/watcher_cycle_ledger.py
tools/signal_closer.py
tools/run_signal_closer_live.sh
tools/be_shadow_manager.py
tools/run_shadow_manager.sh
tools/send_tg.sh
```

## One resurrection authority

Exactly one component may create/recreate the runtime: the **minimal owner/restarter**.

It must:

- own one exclusive lock;
- start at most one runtime instance;
- wait for clean runtime exit;
- restart after runtime crash/kill;
- read persisted useful-progress state;
- declare the runtime a living zombie when useful work exceeds its allowed staleness window;
- force-kill a zombie runtime and start exactly one replacement;
- never execute trading logic itself.

The Python runtime also owns a separate runtime-instance lock so accidental manual launch cannot create a duplicate runtime.

## Useful-progress contract

Required persisted health state must include at least:

```text
runtime_instance_id
runtime_start_utc
heartbeat_write_utc
last_market_data_success_utc
last_indicator_update_utc
last_watcher_cycle_complete_utc
last_signal_decision_utc
last_closer_cycle_complete_utc
last_shadow_cycle_complete_utc
last_clock_validation_utc
last_external_delivery_attempt_utc
clock_trust_state
market_session_state
last_cycle_error_class
```

PID existence alone is never sufficient.

A runtime is a living zombie when its PID exists but required useful-work fields fail to advance beyond their declared market-state-aware deadline. Exact timing values belong in the implementation contract and tests, not as hidden magic constants.

Zombie action:

```text
FORCED_PROCESS_EXIT_AND_EXTERNAL_RESTART
```

## Crash-consistency contract

Every externally visible side effect must use durable intent-before-action semantics:

```text
persist unique operation intent
-> perform external side effect
-> persist confirmed terminal state
```

If the runtime dies after the side effect but before local confirmation, restart must classify the operation as `unknown_outcome` and reconcile before any replay. Blind re-send is forbidden.

State that must survive hard kill includes:

- signal/outbox intent;
- Telegram send state;
- dedupe state;
- open signal lifecycle;
- closer state;
- shadow state where required for outcome integrity;
- last-cycle progress timestamps needed for restart reasoning.

Market-data and indicator caches may be rebuilt.

## Android suspend / Doze contract

Missed timer execution is expected on Android.

On resume:

1. detect the scheduling gap;
2. do not replay missed scans;
3. revalidate trusted time;
4. refetch/validate current market data;
5. reject stale/incomplete candles;
6. resume only from a fresh decision boundary.

No signal may be emitted from stale pre-suspend state.

## Legacy runtime retirement decision

```text
RUNIT=REMOVE_COMPLETELY_AT_CUTOVER
RUNSVDIR=REMOVE_COMPLETELY_AT_CUTOVER
BOT_A_CRON_RESTART_AUTHORITY=REMOVE_COMPLETELY
PROFILE_D_PRODUCTION_LAUNCH=FORBIDDEN
BARE_CROND_FALLBACK=REMOVE
```

Old runit may remain physically present only until the replacement passes acceptance and cutover is executed. It is not a fallback architecture after cutover.

Legacy `runsvdir` death provenance is **useful but not required** before building or cutting over, provided the replacement passes the Android hard-kill/shadow tests. The architecture decision does not revert to runit based on whether the old manager died from SIGTERM, SIGKILL, normal exit, or Android LMK.

## Cutover acceptance contract

The replacement may not cut over because it merely starts or runs for five minutes.

Mandatory gates:

1. **Static/unit:** syntax, lint, unit tests, one owner, one runtime lock, no uncontrolled subprocess creation, deadlines enforced.
2. **Engine parity:** fixed candle fixtures produce the same decision class, score semantics, filters, BUY/SELL/HOLD, SL/TP, Telegram eligibility, and ledger outcome as the existing engine path.
3. **Fault injection:** SIGTERM, SIGKILL, hung OANDA, hung Telegram, DNS failure, Supabase failure, corrupt transient cache, stale clock, suspend/resume, kill during Telegram delivery, kill during ledger persistence.
4. **Restart:** exactly one runtime returns; persistent state remains valid; no duplicate signals; stale market data rejected; trusted clock revalidated; useful work resumes.
5. **Android:** screen off, app backgrounded, charging/non-charging, long unattended interval, wake-lock behavior, battery optimization settings, reboot startup.
6. **Shadow-live:** minimum 7 consecutive days; preferred 10–14 days. No unexplained useful-progress gaps, no duplicate actions, no unresolved crash-consistency anomalies, and no engine parity drift.

Any failure in single-owner, parity, crash consistency, zombie recovery, duplicate prevention, or shadow-live integrity blocks cutover.

## Runtime reliability vs strategy proof

These are separate gates.

### Runtime gate

Question: can BotA execute correctly and continuously enough to produce trustworthy evidence?

### Strategy gate

Question: does BotA produce economically useful signals?

The strategy proof target is approximately **>=60% closed-signal win rate**, but the repo must not treat raw win rate as sufficient. Also measure:

- expectancy;
- average win;
- average loss;
- payoff/R multiple;
- profit factor;
- maximum drawdown;
- unresolved outcomes;
- duplicate/excluded-signal counts;
- sample-selection bias.

Initial evidence should use at least **100 closed signals**; **200+** is preferred before making a strong hosting/economic decision.

## Cloud decision

```text
CLOUD_NOW=NO
CLOUD_AFTER_STRATEGY_PROOF=YES
```

Android remains a temporary evidence-collection host. If the simplified replacement still cannot survive the required Android shadow test, the phone fails the runtime-hosting gate and Linux/VPS migration becomes necessary even before final strategy statistics are complete.

Expected future VPS class remains low-cost rather than premium infrastructure: approximately low-single-digit monthly cost for a very small VM and roughly low-teens for a modest Python/pandas-capable VM, subject to then-current pricing.

## Final decision

```text
FINAL_GO_NO_GO=GO_BUILD
ARCHITECTURE=OPTION_A_CONSTRAINED
PERSISTENT_PROCESS_COUNT=2
ONE_RESURRECTION_AUTHORITY=MINIMAL_OWNER_RESTARTER
RUNTIME=LIGHTWEIGHT_PYTHON_ORCHESTRATOR
ENGINE_EXECUTION=EXISTING_SCRIPTS_AS_BOUNDED_SUBPROCESSES
RUNIT=RETIRE
CRON_RESTART_AUTHORITY=RETIRE
STRATEGY_CHANGE=NO
NEXT_PACKAGE=R1_OWNER_RESTARTER_CONTRACT
```

Do not reopen the architecture debate unless implementation discovers a fatal condition that invalidates the two-process model, such as inability to enforce single ownership, irreconcilable crash-consistency, persistent parity drift, or Android repeatedly killing the simplified topology during the required shadow gate.
