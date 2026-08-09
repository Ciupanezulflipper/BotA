# BotA Current Continuity State

Last updated: **2026-08-09 UTC**

This file is the current operational handoff. Historical audits and `ERRORS.md` preserve prior incidents; do not reconstruct present production state from older snapshots.

## Current authoritative status

```text
GITHUB_MAIN=5cbfbf11fd98d9a40b1d5ea28995f584ec9da080
PHONE_LOCAL_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_LOCAL_HEAD=4339543551aae2e2bcbf727aefe96e3eb103b665
PHONE_WORKTREE_DIRTY=YES

PACKAGE_1_CLOCK_SESSION=PASS
PACKAGE_2_CONTROL_PLANE_RECOVERY=PASS
PACKAGE_2_FINALIZER_DEPLOY=PASS
PR87_PR88_PHONE_DEPLOY=PASS
RUNTIME_DEPENDENCY_CONTRACT=PASS
REQUESTS_VERSION=2.34.2
NATURAL_SHADOW_CYCLE=PASS
PRE_MARKET_PRODUCTION_INTEGRITY=PASS
PRE_MARKET_FAILURE_COUNT=0

CURRENT_CONTROL_PLANE=HEALTHY
CURRENT_MANAGER_COUNT=1
CURRENT_REQUIRED_SERVICES_OWNED=7/7
CURRENT_REQUIRED_SERVICES_RUNNING=7/7
CURRENT_ORPHANED_RUNSV=0
CURRENT_DUPLICATE_SERVICE_ROWS=0
WATCHDOG_SINGLETON=PASS
WATCHDOG_LOCK_SINGLETON=PASS
BOOT_WATCHDOG_PERSISTENCE=PASS
CRON_OWNERSHIP=PASS
RUNTIME_PARITY=PASS
PRODUCTION_CONFIG=PASS
PROFITLAB_STATE=PASS
TRUSTED_CLOCK=PASS

PR89_WATCHDOG_GUARDIAN=BLOCKED_REVIEW_AND_CI
OPEN_MARKET_THREE_PAIR_LIVE_PROOF=PENDING
MONDAY_READY=NO
```

## Latest phone proofs

### Native watchdog finalizer

Phone acceptance after the hash-pinned Package #2 finalizer:

```text
manager_count=1
owned=7/7
running=7/7
orphaned=0
duplicates=0
watchdog_pid=18153
watchdog_lock_holder=18153
finalizer_acceptance=PASS
```

The finalizer also installed the managed Termux:Boot watchdog block. No rollback was required.

### PR #87 / PR #88 production fixes

Phone deployed exact GitHub content from:

```text
5cbfbf11fd98d9a40b1d5ea28995f584ec9da080
```

Deployed/verified:

```text
tools/pre_market_integrity.py
requirements-runtime.txt
tools/runtime_dependency_check.py
tools/run_shadow_manager.sh
requests==2.34.2
```

Safety proof:

```text
PIP_EXISTING_DISTRIBUTION_CHANGE=NO
PIP_BASELINE_UNCHANGED=PASS
CONTROL_PLANE=7_OF_7_HEALTHY
WATCHDOG_SINGLETON=PASS
PROFITLAB_PRESERVED=PASS
SERVICE_RESTARTED=NO
SHADOW_MANUALLY_EXECUTED=NO
STRATEGY_CHANGED=NO
```

### Natural shadow-cycle proof

A natural runit-owned shadow cycle after dependency deployment produced:

```text
SHADOW_STATUS=completed
SHADOW_DETAILS=exit_code=0
LATEST_SHADOW_HEARTBEAT=2026-08-09T14:57:12.073212+00:00 | OK | 0 active signals
LATEST_SHADOW_DONE_LOG=Shadow Manager done | 0 active signals
NATURAL_SHADOW_ACCEPTANCE=PASS
```

### Corrected pre-market integrity gate

The corrected PR #87 gate ran against `5cbfbf11fd98d9a40b1d5ea28995f584ec9da080` and returned:

```text
CHECK_CONTROL_PLANE=PASS
CHECK_WATCHDOG_OWNERSHIP=PASS
CHECK_BOOT_PERSISTENCE=PASS
CHECK_CRON_OWNERSHIP=PASS
CHECK_RUNTIME_PARITY=PASS
CHECK_PRODUCTION_CONFIG=PASS
CHECK_PROFITLAB=PASS
CHECK_PROGRESS=PASS
CHECK_TRUSTED_CLOCK=PASS
FAILURE_COUNT=0
PRE_MARKET_INTEGRITY_ACCEPTANCE=PASS
```

## Production scope remains frozen

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

No strategy threshold, pair/timeframe, Telegram eligibility, or ProfitLab semantics were changed by the readiness work.

## Current blocker: PR #89 watchdog persistence guardian

PR #89 is **not deployable yet**. Current head:

```text
PR89_HEAD=4f73a999634bc83c52defb0d31bfb72291ac83b9
PR89_STATE=OPEN
PR89_DEEPSOURCE_PYTHON=FAIL
```

Still-valid unresolved review findings include:

1. determine advisory lock ownership from active `FLOCK` state rather than merely open descriptors;
2. shell-quote/reject line breaks in CLI-derived cron paths;
3. preserve controlled failure RC/output when event logging itself fails;
4. replace incomplete grep-based process-termination prohibition with AST-based validation and negative fixtures;
5. validate the fully rendered cron entry and exactly one active `--ensure` guardian invocation;
6. reject non-finite timeout values;
7. clean remaining lint/test-quality findings.

Do not deploy or fault-inject PR #89 on the phone until its exact-head CI/static/review gates pass.

## Current freeze

```text
DO_NOT_BOOTSTRAP_PROFITLAB=YES
DO_NOT_LOWER_THRESHOLDS=YES
DO_NOT_FORCE_SIGNAL_COUNT=YES
DO_NOT_FORCE_TELEGRAM_TEST_SIGNAL=YES
DO_NOT_DEPLOY_PR89_BEFORE_REVIEW_GATES=YES
DO_NOT_DECLARE_MONDAY_READY_BEFORE_OPEN_MARKET_PROOF=YES
```

## Exactly one next engineering action

Fix PR #89 on its existing branch `fix/watchdog-persistence-guardian-20260809`, resolve every still-valid review finding, run exact-head CI/static tests, and obtain review-clean status. Only after that should the guardian be deployed to the phone and fault-injection tested.

After the guardian acceptance passes, the final readiness gate is one genuine `MARKET_OPEN` cycle proving current EURUSD:M15, GBPUSD:M15, and USDJPY:M15 decisions in the same authoritative cycle with fresh updater/shadow/data evidence, trusted server time, unique execution ownership, and one authoritative terminal watcher outcome. Three legitimate rejected decisions are acceptable; Telegram delivery is not required.
