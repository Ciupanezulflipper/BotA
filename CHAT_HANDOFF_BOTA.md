# BotA Chat Handoff

Last updated: **2026-08-10 UTC**

Read this first in any new AI session before proposing BotA changes.

## Current grounded answer

```text
TRADING_ENGINE=PROVEN_CAPABLE
CURRENT_LEGACY_RUNTIME=RUNIT_RUNSVDIR_ON_ANDROID
CURRENT_LEGACY_RUNTIME_RELIABILITY=UNTRUSTED_OVER_TIME
TARGET_ARCHITECTURE=OPTION_A_CONSTRAINED
PERSISTENT_PROCESS_COUNT=2
ONE_RESURRECTION_AUTHORITY=MINIMAL_OWNER_RESTARTER
ORCHESTRATOR=LIGHTWEIGHT_PYTHON
ENGINE_EXECUTION=EXISTING_SCRIPTS_AS_BOUNDED_SUBPROCESSES
FINAL_GO_NO_GO=GO_BUILD
PRODUCTION_CUTOVER=NOT_STARTED
CLOUD_NOW=NO
STRATEGY_CHANGED=NO
```

## Canonical final audit

`audits/REPLACEMENT_RUNTIME_SIX_MODEL_ARCHITECTURE_AUDIT_2026-08-10.md`

This records the six-model audit from Claude, Kimi, DeepSeek, Grok, Gemini, and Perplexity and the final synthesis.

## Final architecture

```text
Termux:Boot
    |
    v
minimal owner/restarter
    |
    v
lightweight Python orchestrator
    |
    +-- existing BotA trading-engine entrypoints as transient subprocesses
```

Exactly one component may resurrect the runtime: the owner/restarter.

The orchestrator must stay lightweight. Heavy pandas/indicator/trading logic remains in existing short-lived engine processes during migration.

## What is being retired

At successful cutover:

```text
runit=remove
runsvdir=remove
BotA cron restart authority=remove
profile.d production launch=forbidden
bare crond fallback=remove
watchdogs watching watchdogs=remove
```

These may still exist in the legacy deployed phone before cutover. Do not confuse current legacy deployment with target architecture.

## Health model

PID/process existence is insufficient.

Persisted useful-work state must prove actual progress:

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

A live PID with stale required progress is a living zombie and must be force-exited; the owner then restarts exactly one replacement.

## Trading engine is frozen during migration

```text
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
POLICY_B_ENABLED=1
POLICY_B_SCORE_MIN=70
POLICY_B_ADX_MAX=30
NEWS_ON=0
TELEGRAM_ENABLED=1
DRY_RUN_MODE=0
```

Do not lower thresholds or change strategy semantics to create more signals.

The replacement orchestrator must invoke the existing engine entrypoints and prove parity with fixed fixtures before cutover.

## Crash consistency

External side effects use:

```text
persist intent
-> execute action
-> persist confirmation
```

Unknown completion after a crash must be reconciled. Never blindly resend a possibly delivered signal.

## Android resume rule

After suspend/Doze or scheduling gaps:

```text
do_not_replay_missed_scans
revalidate_trusted_clock
refresh_market_data
reject_stale_or_incomplete_candles
resume_from_fresh_boundary_only
```

## Cutover gate

The replacement must pass:

1. static/unit validation;
2. exact engine parity;
3. SIGTERM/SIGKILL and hung-provider fault injection;
4. crash-consistency tests;
5. duplicate-prevention tests;
6. living-zombie recovery;
7. screen-off/background/reboot/unattended Android tests;
8. minimum 7-day shadow-live run, preferably 10–14 days.

No five-minute success is sufficient.

## Strategy proof after runtime proof

Runtime reliability and profitability are separate.

Initial strategy evidence requires at least 100 closed signals; 200+ preferred. Evaluate >=60% win rate together with positive expectancy, average win/loss, R multiple, profit factor, drawdown, unknown outcomes, duplicates/exclusions, and sample-selection bias.

## Cloud decision

```text
CLOUD_NOW=NO
CLOUD_AFTER_STRATEGY_PROOF=YES
```

If Android cannot pass the simplified architecture's unattended shadow test, cloud/Linux becomes required as a proof host regardless of unfinished strategy statistics.

## GitHub location

```text
BRANCH=docs/final-runtime-architecture-20260810
PR=96
```

The architecture documentation is not a production deployment.

## Exactly one next action

**Package R1: build/test the minimal owner-restarter against a dummy runtime only.**

R1 acceptance:

```text
exactly_one_owner
at_most_one_runtime
normal_exit_restart
SIGTERM_restart
SIGKILL_restart
duplicate_owner_rejected
duplicate_runtime_rejected
stale_useful_progress_detected
corrupt_or_missing_heartbeat_handled
rapid_crash_loop_bounded_and_observable
production_runtime_unchanged
strategy_unchanged
```
