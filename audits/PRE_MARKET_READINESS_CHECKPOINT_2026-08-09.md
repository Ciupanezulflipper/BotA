# BotA Pre-Market Readiness Checkpoint — 2026-08-09

This checkpoint records verified phone/runtime evidence after the Package #2 finalizer and the merged PR #87 / PR #88 production fixes. It supersedes older current-state descriptions but does not rewrite historical audits.

## Repository baseline

```text
CHECKPOINT_BASE_MAIN=163eae4ee7a0d651ed0ad3516dba7eaef4c09cbe
PHONE_RUNTIME_SOURCE_BASELINE=5cbfbf11fd98d9a40b1d5ea28995f584ec9da080
PR87_PR88_BASELINE=5cbfbf11fd98d9a40b1d5ea28995f584ec9da080
PHONE_LOCAL_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_LOCAL_HEAD=4339543551aae2e2bcbf727aefe96e3eb103b665
PHONE_WORKTREE_DIRTY=YES
```

`CHECKPOINT_BASE_MAIN` is the main commit used as the documentation base. The documentation merge containing this file advances `main`; issue #9 carries the live current-main SHA. The phone runtime acceptance remains pinned to reviewed runtime source baseline `5cbfbf11...`.

The phone checkout HEAD is not the production deployment identity; deployment acceptance is based on exact reviewed blobs, runtime state, and bounded postconditions.

## Package #2 control-plane recovery

The watchdog recovery moved the phone from the previously observed orphaned topology back to the required native-manager topology. Final verified state:

```text
MANAGER_COUNT=1
OWNED=7
RUNNING=7
ORPHANED=0
DUPLICATES=0
HEALTHY=True
```

The Package #2 finalizer then passed independently:

```text
NATIVE_WATCHDOG_FINALIZER_DEPLOY=PASS
CONTROL_PLANE=7_OF_7_HEALTHY
WATCHDOG_SINGLETON=PASS
WATCHDOG_LOCK_SINGLETON=PASS
ROLLBACK_EXECUTED=NO
```

Observed watchdog/lock identity at the finalizer checkpoint:

```text
WATCHDOG_PID=18153
LOCK_HOLDER=18153
```

The managed Termux:Boot watchdog block also passed finalization.

## PR #87 / PR #88 phone deployment

The following reviewed runtime artifacts were deployed from exact GitHub runtime source commit `5cbfbf11fd98d9a40b1d5ea28995f584ec9da080`:

```text
tools/pre_market_integrity.py
requirements-runtime.txt
tools/runtime_dependency_check.py
tools/run_shadow_manager.sh
```

Runtime dependency:

```text
requests==2.34.2
python=3.14.6
DEPENDENCY_CONTRACT=PASS
```

The pre-existing Termux Python environment already reported unsupported-platform warnings for contourpy, matplotlib, numpy, and pillow. Deployment used a baseline-regression contract instead of requiring a false-clean environment:

```text
PIP_PLAN_EXISTING_DISTRIBUTION_CHANGE=NO
PIP_CHECK_BEFORE_RC=1
PIP_CHECK_AFTER_RC=1
PIP_BASELINE_UNCHANGED=PASS
```

The deploy preserved production state:

```text
CONTROL_PLANE=7_OF_7_HEALTHY
WATCHDOG_SINGLETON=PASS
PROFITLAB_PRESERVED=PASS
SERVICE_RESTARTED=NO
SHADOW_MANUALLY_EXECUTED=NO
STRATEGY_CHANGED=NO
ROLLBACK_EXECUTED=NO
```

## Natural shadow-cycle acceptance

After dependency deployment, the existing runit cadence naturally executed the shadow manager. Acceptance evidence:

```text
DEPENDENCY_HEALTHY=True
REQUESTS_VERSION=2.34.2
LEDGER_BOOT_ID=b32a66a6-1a91-4b61-b759-c32851cbae6b
SHADOW_STATUS=completed
SHADOW_DETAILS=exit_code=0
LATEST_SHADOW_HEARTBEAT=2026-08-09T14:57:12.073212+00:00 | OK | 0 active signals
LATEST_SHADOW_DONE_LOG=Shadow Manager done | 0 active signals
NATURAL_SHADOW_ACCEPTANCE=PASS
```

No manual shadow execution and no service restart were used for this proof.

## Corrected pre-market integrity gate

The corrected PR #87 gate was run read-only against runtime source baseline `5cbfbf11...` and returned:

```text
INTEGRITY_HEALTHY=True
PROCESS_RC=0
MUTATED=False
STRATEGY_CHANGED=False
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

Therefore:

```text
INFRASTRUCTURE_AND_CLOSED_MARKET_READINESS=PASS
```

This is **not** equivalent to `MONDAY_READY=YES`.

## Remaining blocker — PR #89

PR #89: `fix: persist native watchdog with fail-closed cron guardian`

```text
PR89_STATE=OPEN
PR89_HEAD=4f73a999634bc83c52defb0d31bfb72291ac83b9
PR89_MERGEABLE=true
DEEPSOURCE_PYTHON=failure
MONDAY_READY=NO
```

Do not deploy PR #89 until exact-head CI/static/review gates pass. Still-valid unresolved findings include:

1. guardian lock ownership must be derived from active advisory `FLOCK`, not any process merely holding an open descriptor to the lock file;
2. rendered cron CLI paths must use shell-safe quoting and reject CR/LF injection;
3. event-log write failure must not mask the guardian's controlled failure status/RC;
4. the no-process/service-termination CI guard must be AST-based and cover equivalent APIs/command forms with negative fixtures;
5. CI must validate the complete rendered crontab and prove exactly one active managed `--ensure` guardian invocation;
6. non-finite timeout arguments must be rejected;
7. remaining lint/test-quality findings must be cleaned.

## Remaining production readiness gates

```text
PR89_REVIEW_CLEAN=PENDING
PR89_EXACT_HEAD_CI=FAIL_CURRENTLY
PR89_PHONE_DEPLOYMENT=PENDING
PR89_FAULT_INJECTION_RECOVERY=PENDING
OPEN_MARKET_THREE_PAIR_LIVE_PROOF=PENDING
MONDAY_READY=NO
```

After PR #89 is fixed, reviewed, merged, deployed, and fault-injection accepted, the final production gate is one genuine `MARKET_OPEN` M15 cycle proving EURUSD, GBPUSD, and USDJPY in the same current cycle with fresh updater/shadow/data evidence, trusted server time, unique ownership, and one authoritative terminal watcher outcome. Three legitimate rejects are acceptable; Telegram delivery is not required.

## Strategy freeze

```text
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
POLICY_B_ENABLED=1
POLICY_B_SCORE_MIN=70
POLICY_B_ADX_MAX=30
NEWS_ON=0
DO_NOT_LOWER_THRESHOLDS=YES
DO_NOT_FORCE_TELEGRAM_SIGNAL=YES
DO_NOT_BOOTSTRAP_PROFITLAB=YES
```
