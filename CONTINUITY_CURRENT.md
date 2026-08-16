# BotA Current Continuity State

Last updated: **2026-08-10 UTC**

This file is the current operational handoff. Historical runit repair work remains in Git history and dated audits, but it no longer defines the target architecture.

## Current authoritative status

```text
PROJECT=BOTA
TRADING_ENGINE=PROVEN_CAPABLE
SIGNAL_GENERATION=PROVEN
TELEGRAM_DELIVERY=PROVEN
MARKET_SCANNING=PROVEN
CURRENT_LEGACY_RUNIT_CONTROL_PLANE=UNSTABLE_OVER_TIME
TARGET_ARCHITECTURE=OPTION_A_CONSTRAINED
FINAL_GO_NO_GO=GO_BUILD
PRODUCTION_CUTOVER=NOT_STARTED
STRATEGY_CHANGED=NO
CLOUD_NOW=NO
```

## Canonical architecture decision

The six-model final design audit is recorded at:

`audits/REPLACEMENT_RUNTIME_SIX_MODEL_ARCHITECTURE_AUDIT_2026-08-10.md`

The locked replacement is:

```text
Termux:Boot
    |
    v
minimal owner/restarter
    |
    v
lightweight Python orchestrator
    |
    +-- existing BotA engine entrypoints as bounded transient subprocesses
```

Exactly two persistent processes are targeted:

```text
1=minimal owner/restarter
2=Python orchestrator
```

The owner/restarter is the **only resurrection authority**. The Python orchestrator owns no competing resurrection logic.

## Superseded architecture path

The previous target of continuing to harden:

```text
termux-services
runit
runsvdir
7 runsv supervisors
cron watchdog guard
profile/boot launch overlap
native watchdog recovery
bare-crond fallback
```

is superseded as the target architecture.

Do not continue the old repair loop simply because the currently deployed phone still uses it. Legacy runtime state is operational evidence only until cutover.

## Trading-engine preservation

The migration is an orchestration change, not a strategy rewrite.

The current engine behavior remains frozen. Major entrypoints include:

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

Recently verified phone-vs-current-main parity established that the seven previously modified trading-engine files were already identical to current GitHub main. The only genuine phone-only tracked mutation found during classification was the explicit-`SVDIR` watchdog launcher, and that content was preserved on branch `preserve/svdir-launcher-20260810` at commit `99d297bffe5f3f4ffe40275279ebf281e24615cb`.

## Current production scope remains frozen

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

Do not lower thresholds, change pair/timeframe scope, or manufacture signal activity during runtime migration.

## Useful-work health contract

The replacement must never equate an existing PID with health.

Required persisted progress includes at least:

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

A live runtime whose required work exceeds its declared staleness deadline is a **living zombie**. Required action:

```text
FORCED_PROCESS_EXIT_AND_EXTERNAL_RESTART
```

## Crash-consistency and fail-closed rules

Before any externally visible side effect:

```text
persist unique intent
-> perform side effect
-> persist confirmed terminal state
```

If the process dies after the side effect but before confirmation, restart must classify the operation as `unknown_outcome` and reconcile before replay.

Blind resend is forbidden.

No new signal may be emitted when trusted clock, market-data freshness, required persistent state, or closer safety is ambiguous.

## Android suspend / Doze rule

Missed timers are expected on Android.

After a scheduling gap:

1. detect resume gap;
2. do not replay missed scans;
3. revalidate trusted time;
4. refresh market data;
5. prove candle freshness/completeness;
6. resume only from a fresh decision boundary.

## Cutover gates

The replacement is not production-ready because it starts or runs for five minutes.

Required acceptance families:

```text
STATIC_UNIT
ENGINE_PARITY
FAULT_INJECTION
RESTART_AND_DUPLICATE_PREVENTION
ANDROID_SCREEN_OFF_BACKGROUND_UNATTENDED
CRASH_CONSISTENCY
SHADOW_LIVE
```

Minimum shadow-live duration: **7 consecutive days**. Preferred: **10–14 days**.

## Runtime proof vs strategy proof

These are separate.

Runtime proof asks whether BotA can produce trustworthy evidence continuously.

Strategy proof asks whether the signals are economically useful.

Current strategy proof target:

```text
WIN_RATE_TARGET=>=60_PERCENT
EXPECTANCY=>0
DUPLICATE_SIGNALS=0
UNKNOWN_OUTCOMES=0_FOR_EVALUATED_SAMPLE
MIN_CLOSED_SIGNALS_INITIAL=100
PREFERRED_CLOSED_SIGNALS=200_PLUS
```

Win rate alone is not sufficient; also record average win, average loss, R multiple/payoff ratio, profit factor, maximum drawdown, unresolved outcomes, and sample-selection rules.

## Cloud decision

```text
CLOUD_NOW=NO
CLOUD_AFTER_STRATEGY_PROOF=YES
```

Exception: if the simplified two-process runtime repeatedly fails the required Android unattended/shadow gate, the phone fails as a proof host and Linux/VPS migration becomes operationally necessary even before final strategy statistics are complete.

## Repository branch / PR

Final architecture documentation is being recorded on:

```text
BRANCH=docs/final-runtime-architecture-20260810
PR=96
```

No production runtime mutation is implied by this documentation branch.

## Exactly one next engineering action

**Package R1 — owner/restarter contract only.**

Build and test the minimal owner/restarter against a dummy runtime. Do not connect the trading engine yet.

R1 must prove:

```text
exactly_one_owner
at_most_one_runtime
normal_exit_restart
SIGTERM_restart
SIGKILL_restart
duplicate_owner_rejected
duplicate_runtime_rejected
PID_alive_but_stale_progress_detected
corrupt_or_missing_heartbeat_handled
rapid_crash_loop_bounded_and_observable
production_runtime_not_mutated
strategy_not_changed
```

Only after R1 passes should the Python orchestrator package begin.
