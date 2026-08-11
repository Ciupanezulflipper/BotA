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
CURRENT_ARCHITECTURE_DECISION=OPTION_A_PROCESS_ISOLATED_RUNTIME
STRATEGY_THRESHOLDS=FROZEN
CLOUD_MIGRATION=DEFERRED_UNTIL_STRATEGY_PROVES_ITSELF
PRODUCTION_TRADING_READY=NO
```

The trading engine has demonstrated that it can scan markets, produce actionable decisions, and deliver Telegram signals. The unresolved problem is runtime/control-plane persistence on Android/Termux.

Canonical final audit: `audits/REPLACEMENT_RUNTIME_SIX_MODEL_ARCHITECTURE_AUDIT_2026-08-10.md`.

Do not infer current production state from old backtests, `BOTLOG.md`, `BOOTLOG.md`, historical continuity entries, or an Android working-tree HEAD.

## Final runtime architecture decision — 10 August 2026

After repeated HEALTHY → DEGRADED → RECOVERY oscillation, a six-model forensic review of the existing runit failure, and a second six-model adversarial architecture audit, the replacement runtime is now locked.

```text
ARCHITECTURE=OPTION_A_PROCESS_ISOLATED_RUNTIME
PERSISTENT_PROCESS_COUNT=2
PROCESS_1=MINIMAL_EXTERNAL_OWNER_RESTARTER
PROCESS_2=PYTHON_ORCHESTRATOR
TRADING_ENGINE_INTEGRATION=EXEC_EXISTING_MODULES_AS_SUBPROCESSES
RUNIT=REMOVE_COMPLETELY
RUNSVDIR=REMOVE_COMPLETELY
BOT_A_CRON_RESTART_AUTHORITY=REMOVE_COMPLETELY
PROFILE_STARTUP_RUNTIME_MUTATION=FORBIDDEN
TERMUX_BOOT=BOOTSTRAP_ONLY
CLOUD_NOW=NO
CLOUD_AFTER_STRATEGY_PROOF=YES
```

This is an orchestration replacement, not a trading-strategy rewrite.

### Why this architecture was selected

The previous control plane failed because ownership and recovery were distributed across too many actors. The replacement deliberately minimizes the persistent topology while preserving the proven engine exactly.

The selected model is:

```text
Termux:Boot
    |
    v
minimal owner/restarter
    |
    v
Python orchestrator
    |
    +-- transient existing BotA scripts/tools
```

The owner/restarter contains no trading logic. It owns exactly one runtime instance, checks actual useful-work progress, and restarts only that runtime when the runtime is dead or objectively stale.

The Python orchestrator does not absorb the trading engine into one large imported application. It executes the already-proven shell/Python entrypoints as bounded subprocesses. This preserves engine parity, releases heavy per-cycle memory when subprocesses exit, avoids a large refactor, and keeps the permanent process footprint small.

## Locked process model

### Persistent process 1 — owner/restarter

Responsibilities:

- started once by Termux:Boot;
- holds one exclusive owner lock;
- launches exactly one Python orchestrator;
- records runtime PID and instance identity;
- detects runtime exit;
- detects a living-zombie runtime using persisted useful-progress timestamps;
- force-terminates a provably stale runtime and starts one replacement;
- never runs market-data, scoring, filtering, closer, shadow, or delivery logic.

The owner itself must remain intentionally tiny and dependency-light.

### Persistent process 2 — Python orchestrator

Responsibilities:

- one runtime lock;
- schedule BotA work;
- invoke existing engine scripts as subprocesses;
- apply hard deadlines to every subprocess;
- persist useful-progress timestamps;
- enforce crash-consistency and restart reconciliation;
- fail closed on stale time, stale data, or unreconciled safety-critical state.

The orchestrator must not treat PID existence as health.

### Transient subprocesses

Existing BotA engine entrypoints remain the behavior authority during migration. Heavy Python/pandas work should remain in short-lived subprocesses unless a later, separately reviewed refactor proves parity.

At most a small bounded number of subprocesses may run concurrently. No persistent worker farm is approved.

## Why Option A beat the alternatives

### Versus a three-process worker architecture

A separate monitor worker adds another persistent process, IPC, another failure surface, and another state channel without solving a problem that the tiny owner can solve by reading the runtime heartbeat directly.

### Versus a shell-only supervisor

A shell-only loop is attractive for simplicity but cannot credibly provide the same crash-consistency, structured progress accounting, stale-runtime classification, restart reconciliation, and durable state handling without becoming a custom supervision framework in shell.

### Versus a fully imported one-process Python application

A monolithic imported runtime would increase migration risk, concentrate memory, and create a larger silent-deadlock blast radius. The approved design keeps the orchestrator small and executes proven components as bounded subprocesses.

### Versus cloud immediately

A Linux VPS is the preferred long-term host, but BotA must first prove economic value. Infrastructure spending is deferred until the strategy produces trustworthy performance evidence.

## Resurrection authority

Exactly one component may resurrect the BotA runtime: the minimal owner/restarter.

No other component may independently start or replace the runtime.

Forbidden resurrection paths:

- profile.d startup;
- `.bashrc` runtime launch;
- crond runtime restart;
- native watchdog replacement loops;
- runit/runsvdir;
- service-daemon;
- duplicate Termux:Boot invocations that bypass the owner lock.

Termux:Boot is a bootstrap source, not a recurring resurrection authority.

If Android kills every Termux process, local automatic recovery is not guaranteed until Android/Termux is started again or the device reboots. This residual Android limitation is accepted during the proof phase and must be covered by external silence detection/alerting, not by adding another competing local restarter.

## Useful-progress liveness contract

The runtime heartbeat must be persisted atomically and include at least:

```text
runtime_instance_id
runtime_start_utc
runtime_pid
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
cycle_count_total
last_cycle_error_class
```

Recommended diagnostics:

```text
rss_bytes
open_fd_count
last_oanda_success_utc
last_telegram_success_utc
last_supabase_success_utc
last_resume_detected_utc
```

A runtime is a living zombie when its PID exists but useful work has stopped beyond a declared deadline.

During market-open conditions, initial implementation should treat either of these as fatal until tuned from real cadence data:

```text
watcher progress stale > 3 expected watcher intervals
clock validation stale beyond trusted-clock TTL
closer progress stale > 3 closer intervals while open signals exist
heartbeat snapshot stale > 3 heartbeat intervals
```

Zombie action:

```text
FORCED_PROCESS_EXIT_AND_EXTERNAL_RESTART
```

The owner must never infer health from `ps` alone.

## Network and subprocess deadline contract

No network or subprocess operation may block indefinitely.

Initial safe implementation ranges:

```text
CONNECT_TIMEOUT=3_TO_10_SECONDS
READ_TIMEOUT=5_TO_20_SECONDS
PER_OPERATION_DEADLINE=15_TO_30_SECONDS_FOR_NORMAL_API_CALLS
TOTAL_RETRY_BUDGET=30_TO_90_SECONDS
RETRIES=BOUNDED_TRANSIENT_ERRORS_ONLY
BACKOFF=EXPONENTIAL_WITH_JITTER
```

Longer computational subprocesses may have explicitly larger task-specific deadlines, but every child must have both a soft timeout and a hard-kill deadline.

No retry path may starve closer work or trusted-clock validation.

## Trading-engine integration

Locked migration model:

```text
EXEC_EXISTING_MODULES_AS_SUBPROCESSES
```

Do not refactor the proven engine into imported long-lived modules during the runtime migration.

Parity-critical engine files include:

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

The recent phone-vs-current-main capture already proved parity for the seven previously disputed trading-engine files. Runtime migration must preserve those bytes/semantics unless a separate behavior change is intentionally approved.

## Crash-consistency contract

Every externally visible side effect must use durable intent before execution and durable confirmation after execution.

Required pattern:

```text
1. create durable operation_id + dedupe key
2. persist state=prepared
3. perform external side effect
4. persist terminal state=sent/committed/closed/reconciled
5. on restart, reconcile prepared/unknown_outcome records before replay
```

A crash between the external action and local confirmation must never cause a blind resend.

Safety-critical state that must persist across hard kill includes:

```text
current signal/outbox intent
Telegram send status
dedupe state
open signal lifecycle
closer state
shadow state
last-cycle timestamps
runtime heartbeat
required provider/accounting state that cannot be reconstructed safely
```

Rebuildable state includes market-data caches and indicator caches.

Clock trust must be re-established after restart even if prior clock evidence is retained for diagnostics.

## Fail-closed dependency rules

```text
TRUSTED_CLOCK_FAIL -> NOTHING_NEW_TRADES
STALE_MARKET_DATA -> NO_NEW_SIGNAL
CLOSER_FAIL_WITH_OPEN_SIGNALS -> NO_NEW_SIGNAL
DISK_OR_DURABLE_JOURNAL_FAIL -> NO_NEW_EXTERNAL_SIDE_EFFECT
OANDA_FAIL -> SKIP_CYCLE
TELEGRAM_FAIL -> SCANNING_MAY_CONTINUE, DELIVERY_REMAINS_DURABLY_UNRESOLVED
SUPABASE_FAIL -> CONTINUE_ONLY_IF_LOCAL_DURABLE_EVIDENCE_IS_COMPLETE
HEARTBEAT_STATUS_FAIL -> SHORT_GRACE_ONLY, THEN_RESTART_OR_FAIL_CLOSED
```

Missed opportunities are preferable to ambiguous duplicate or stale actions.

## Android suspend / Doze contract

The runtime must assume that timers can resume late.

After an unexpected timing gap:

1. detect the gap using elapsed-time and wall-clock evidence;
2. do not replay missed scans;
3. revalidate trusted time;
4. refresh market data;
5. prove candle freshness/completeness;
6. discard stale opportunities;
7. only then resume decision generation.

A wake lock may be used where justified, but wake-lock use is not considered proof of Android persistence.

## Memory safety contract

The orchestrator must remain lightweight.

Required monitoring:

```text
RSS trend
open file descriptor count
cycle latency
cache sizes
runtime age
error/retry rate
```

Caches must have hard bounds.

Persistent HTTP pools must have explicit stale-connection handling or periodic renewal.

No fixed RSS kill threshold is locked before a real baseline is measured on the target phone.

Planned periodic restart is not mandatory initially. Add a controlled daily runtime recycle only if soak evidence shows aging/resource degradation.

## Legacy runsvdir death evidence

Capturing one real runsvdir death signal remains:

```text
USEFUL_BUT_NOT_REQUIRED
```

It may improve confidence about Android vs local termination, but it no longer blocks implementation because every plausible outcome still leaves the current multi-authority runit architecture rejected.

Do not delay the replacement build waiting for another old-runtime failure.

## Cutover acceptance contract

The replacement must not cut over because it starts or survives five minutes.

All critical gates below must pass.

### 1. Static / ownership

- exactly one Termux:Boot bootstrap;
- exactly one owner/restarter;
- exactly one runtime lock;
- zero BotA cron restart paths;
- zero profile-start runtime launch paths;
- zero runit/runsvdir ownership in the replacement;
- syntax/lint/tests pass;
- every child/network path has a deadline.

### 2. Trading parity

Using fixed recorded candle fixtures:

```text
same market input
-> same score
-> same filters
-> same BUY/SELL/HOLD
-> same entry
-> same SL
-> same TP
-> same Telegram eligibility
-> same ledger terminal outcome
```

Any unexplained trading-decision drift is an automatic migration failure.

### 3. Fault injection

Must test at least:

```text
SIGTERM runtime
SIGKILL runtime
hung OANDA
hung Telegram
broken DNS
broken Supabase
corrupt transient cache
stale clock
suspend/resume
kill during Telegram delivery
kill during ledger update
hung subprocess that ignores TERM
```

### 4. Restart correctness

Prove after hard failure:

```text
one runtime instance only
no duplicate signal
no silently lost required state
stale data rejected
clock revalidated
useful progress resumes
unknown side effects reconciled
```

### 5. Android reality

Must include:

```text
screen off
app backgrounded
charging
non-charging
long unattended interval
battery optimization configuration documented
wake-lock behavior documented
full reboot / Termux:Boot test
```

### 6. Shadow live gate

Minimum required shadow duration before production cutover:

```text
7_CONSECUTIVE_DAYS_MINIMUM
```

Preferred confidence window:

```text
10_TO_14_DAYS
```

The window must include real market sessions, at least one reboot, screen-off/background operation, network interruption, and forced-kill testing.

Any unexplained duplicate, stale-data action, crash-consistency anomaly, or parity drift fails the gate.

## Strategy proof gate

Runtime reliability proof and strategy performance proof are separate.

After the replacement runtime proves it can collect trustworthy evidence, strategy evaluation begins on a predeclared continuous sample.

Initial evidence threshold:

```text
MINIMUM_CLOSED_SIGNALS=100
PREFERRED_CLOSED_SIGNALS=200_PLUS
WIN_RATE_TARGET=>=60_PERCENT
EXPECTANCY=>0
PROFIT_FACTOR=>1
DUPLICATE_SIGNALS=0
UNKNOWN_OUTCOMES=0_FOR_EVALUATED_SAMPLE
```

Also report:

- confidence interval for win rate;
- average win;
- average loss;
- payoff ratio / R multiple;
- maximum drawdown;
- unresolved/open signals separately;
- spread/cost assumptions;
- all exclusions under predeclared rules.

Do not cherry-pick the evaluation interval and do not lower thresholds to accelerate proof.

## Cloud decision

```text
CLOUD_NOW=NO
CLOUD_AFTER_STRATEGY_PROOF=YES
```

Expected low-cost Linux hosting range when justified:

```text
VERY_SMALL_VPS≈USD_4_TO_8_PER_MONTH
MODEST_PYTHON_PANDAS_VPS≈USD_10_TO_20_PER_MONTH
```

Android is accepted temporarily as the zero-incremental-cost evidence host. Linux/VPS is preferred for long-term operation once BotA proves economic value because it removes Android power-management and background-process constraints and simplifies supervision, SSH access, logging, backup, and recovery.

## Immediate engineering objective

```text
1_FREEZE_TRADING_STRATEGY
2_BUILD_MINIMAL_OWNER_RESTARTER
3_BUILD_LIGHTWEIGHT_PYTHON_ORCHESTRATOR
4_EXECUTE_EXISTING_ENGINE_ENTRYPOINTS_AS_BOUNDED_SUBPROCESSES
5_ADD_ATOMIC_USEFUL_PROGRESS_HEARTBEAT
6_ADD_CRASH_CONSISTENT_INTENT_AND_RECONCILIATION
7_ADD_HARD_NETWORK_AND_SUBPROCESS_DEADLINES
8_RUN_OFFLINE_PARITY_FIXTURES
9_RUN_FAULT_INJECTION
10_RUN_ANDROID_SHADOW_GATE_7_TO_14_DAYS
11_CUT_OVER_ONLY_AFTER_ALL_CRITICAL_GATES_PASS
12_COLLECT_100_TO_200_PLUS_CLEAN_CLOSED_SIGNALS
13_IF_STRATEGY_PROVES_ITSELF_MOVE_TO_LOW_COST_LINUX_VPS
```

Do not reopen the historical runit repair loop unless new evidence proves the selected replacement architecture materially less safe than the old control plane.
