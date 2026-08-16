# BotA AI Start Here

Last updated: **2026-08-10 UTC**

Read this before proposing BotA commands, code, service, strategy, deployment, Android/Termux, or cloud changes.

## Current authoritative truth

```text
PROJECT=BOTA
TRADING_ENGINE_REWRITE=NO
TRADING_ENGINE_BEHAVIOR=FROZEN
CURRENT_LEGACY_RUNIT_RUNTIME=UNSTABLE_OVER_TIME
TARGET_RUNTIME_ARCHITECTURE=OPTION_A_CONSTRAINED
PERSISTENT_PROCESS_COUNT=2
ONE_RESURRECTION_AUTHORITY=MINIMAL_OWNER_RESTARTER
ORCHESTRATOR=LIGHTWEIGHT_PYTHON
ENGINE_INTEGRATION=EXEC_EXISTING_MODULES_AS_BOUNDED_SUBPROCESSES
RUNIT_TARGET=REMOVE_AT_CUTOVER
CRON_RESTART_AUTHORITY_TARGET=REMOVE
PRODUCTION_CUTOVER=NOT_STARTED
FINAL_GO_NO_GO=GO_BUILD
CLOUD_NOW=NO
```

## Canonical six-model audit

Read first:

`audits/REPLACEMENT_RUNTIME_SIX_MODEL_ARCHITECTURE_AUDIT_2026-08-10.md`

That file records the final architecture audit from Claude, Kimi, DeepSeek, Grok, Gemini, and Perplexity, including disagreements and the final synthesis.

## Locked replacement design

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

The owner/restarter is the only component allowed to create/recreate the orchestrator.

Opening a shell must never alter production runtime topology.

No profile.d launcher, cron guardian, runit manager, watchdog chain, or bare-crond fallback may become a second resurrection authority in the replacement.

## Critical health rule

**PID existence is not health.**

Useful-work progress must be persisted. Required fields include:

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

A PID that exists while required useful work is stale beyond its declared deadline is a living zombie.

Required zombie action:

```text
FORCED_PROCESS_EXIT_AND_EXTERNAL_RESTART
```

## Engine preservation rule

Do not refactor the strategy into a monolithic imported Python runtime during migration.

Existing engine entrypoints remain the behavior authority and are invoked as bounded subprocesses. Major files include:

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

Parity testing must prove identical decision semantics for identical input before cutover.

## Strategy/runtime freeze

```text
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
POLICY_B_ENABLED=1
POLICY_B_SCORE_MIN=70
POLICY_B_ADX_MAX=30
NEWS_ON=0
TELEGRAM_ENABLED=1
DRY_RUN_MODE=0
DO_NOT_LOWER_THRESHOLDS=YES
DO_NOT_FORCE_SIGNAL_COUNT=YES
```

Runtime work must not change signal thresholds, pair/timeframe scope, filter policy, or Telegram eligibility.

## Crash consistency

Every externally visible action follows:

```text
persist unique intent
-> execute side effect
-> persist confirmed terminal state
```

A restart that finds an unconfirmed action after a possible external side effect must classify it as `unknown_outcome` and reconcile. Blind replay is forbidden.

## Android timing rule

After suspend/Doze or any scheduling gap:

- do not replay missed scans;
- revalidate trusted time;
- refresh market data;
- reject stale/incomplete candles;
- resume only from a fresh decision boundary.

## Acceptance before cutover

Required gates:

```text
STATIC_UNIT
ENGINE_PARITY
FAULT_INJECTION
RESTART
DUPLICATE_PREVENTION
CRASH_CONSISTENCY
ANDROID_UNATTENDED
SHADOW_LIVE
```

Minimum shadow-live gate: **7 consecutive days**; preferred **10–14 days**.

## Strategy proof is separate

The runtime must first prove trustworthy evidence collection.

Then strategy evidence is evaluated using at least 100 closed signals initially, preferably 200+, with:

```text
win_rate
expectancy
average_win
average_loss
R_multiple_or_payoff_ratio
profit_factor
maximum_drawdown
unresolved_outcomes
duplicate_or_excluded_signal_counts
sample_selection_rules
```

Target >=60% win rate does not override the requirement for positive expectancy.

## Cloud rule

```text
CLOUD_NOW=NO
CLOUD_AFTER_STRATEGY_PROOF=YES
```

If Android cannot pass the simplified runtime's unattended/shadow gate, the phone fails as a proof host and Linux/VPS migration becomes necessary earlier.

## Repository workflow

Normal flow remains:

```text
inspect current truth
-> bounded branch
-> complete-file changes
-> verify exact diff
-> PR
-> exact-head tests/review
-> merge
-> separate deployment gate
```

Never push normal work directly to `main`.

## Read order

1. `README.md`
2. `audits/REPLACEMENT_RUNTIME_SIX_MODEL_ARCHITECTURE_AUDIT_2026-08-10.md`
3. `CONTINUITY_CURRENT.md`
4. `CHAT_HANDOFF_BOTA.md`
5. `state/STATE.json`
6. `DECISIONS.md`
7. `ERRORS.md` and `audits/ERROR_LOG.md`

## Exactly one next engineering action

**Package R1: minimal owner/restarter contract against a dummy runtime only.**

No production phone mutation, trading-engine integration, runit removal, cron removal, or strategy change belongs in R1.
