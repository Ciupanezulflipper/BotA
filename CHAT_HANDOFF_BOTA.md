# BotA Chat Handoff

Last updated: **2026-08-09 UTC**

Read this first in any new AI session before proposing BotA changes.

## Current grounded answer

```text
CHECKPOINT_BASE_MAIN=810441fd772e1330db7de670c3eae95606981742
PHONE_RUNTIME_SOURCE_BASELINE=5cbfbf11fd98d9a40b1d5ea28995f584ec9da080
PHONE_LOCAL_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_LOCAL_HEAD=4339543551aae2e2bcbf727aefe96e3eb103b665
PHONE_WORKTREE_DIRTY=YES

PACKAGE_1_CLOCK_SESSION=PASS
PACKAGE_2_CONTROL_PLANE_RECOVERY=PASS
PACKAGE_2_FINALIZER_DEPLOY=PASS
PR87_PR88_PHONE_DEPLOY=PASS
RUNTIME_DEPENDENCY_CONTRACT=PASS
CURRENT_CONTROL_PLANE=HEALTHY
CURRENT_REQUIRED_SERVICES_OWNED=7/7
CURRENT_REQUIRED_SERVICES_RUNNING=7/7
CURRENT_ORPHANED_RUNSV=0
CURRENT_DUPLICATE_SERVICE_ROWS=0
WATCHDOG_SINGLETON=PASS
BOOT_PERSISTENCE=PASS
PROFITLAB_PRESERVED=PASS
NATURAL_SHADOW_CYCLE=PASS
PRE_MARKET_PRODUCTION_INTEGRITY=PASS
PR89_WATCHDOG_GUARDIAN=BLOCKED_REVIEW_AND_CI
OPEN_MARKET_THREE_PAIR_PROOF=PENDING
MONDAY_READY=NO
```

The phone checkout HEAD is not production identity. Runtime acceptance is based on immutable reviewed source blobs, deployed file parity, runtime state, and bounded postconditions.

## Latest verified phone evidence

The PR #87 / #88 deployment and subsequent natural runtime proof passed:

```text
requests==2.34.2
DEPENDENCY_CONTRACT=PASS
PIP_BASELINE_REGRESSION=NO
CONTROL_PLANE=7_OF_7_HEALTHY
WATCHDOG_SINGLETON=PASS
PROFITLAB_PRESERVED=PASS
SERVICE_RESTARTED=NO
SHADOW_MANUALLY_EXECUTED=NO
STRATEGY_CHANGED=NO
```

A later natural runit-owned shadow cycle completed successfully:

```text
SHADOW_STATUS=completed
SHADOW_DETAILS=exit_code=0
LATEST_SHADOW_HEARTBEAT=OK | 0 active signals
LATEST_SHADOW_DONE_LOG=Shadow Manager done | 0 active signals
NATURAL_SHADOW_ACCEPTANCE=PASS
```

The corrected pre-market integrity gate then passed all nine checks with zero failures:

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

Therefore:

```text
INFRASTRUCTURE_AND_CLOSED_MARKET_READINESS=PASS
```

Do **not** translate that into `MONDAY_READY=YES` yet.

## Current production scope

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

Do not lower thresholds or change signal eligibility to manufacture activity.

## Current blocker — PR #89

PR #89 `fix: persist native watchdog with fail-closed cron guardian` is still open. Current head at this checkpoint:

```text
PR89_HEAD=4f73a999634bc83c52defb0d31bfb72291ac83b9
PR89_MERGEABLE=true
GITHUB_ACTIONS_SECURITY_SCAN=PASS
GITHUB_ACTIONS_NATIVE_WATCHDOG_GUARDIAN=PASS
DEEPSOURCE_PYTHON=FAIL
UNRESOLVED_REVIEW_THREADS=9
```

The unresolved findings are concentrated in the five PR files:

- `.github/workflows/native-watchdog-guardian.yml`
- `tools/native_watchdog_guard.py`
- `tools/native_watchdog_cron_config.py`
- `tests/test_native_watchdog_guard.py`
- `tests/test_native_watchdog_cron_config.py`

Required fixes:

1. active advisory `FLOCK` ownership rather than open-descriptor inference;
2. shell-safe quoted cron paths plus CR/LF rejection;
3. controlled guardian failure even if event logging itself fails;
4. AST-based no-termination validator with negative fixtures;
5. full rendered-crontab validation with exactly one managed active `--ensure` line;
6. finite timeout validation (`NaN` / infinities rejected);
7. `persist-credentials: false` on checkout;
8. unused-variable cleanup;
9. staticmethod cleanup in cron tests.

No phone deployment of PR #89 is allowed until exact-head review/static/CI gates pass.

## Remaining Monday gates

```text
PR89_REVIEW_CLEAN=PENDING
PR89_EXACT_HEAD_STATIC_AND_CI=PASS_REQUIRED
PR89_MERGE=PENDING
GUARDIAN_PHONE_DEPLOY=PENDING
GUARDIAN_WATCHDOG_ONLY_FAULT_INJECTION=PENDING
OPEN_MARKET_EURUSD_M15=PENDING
OPEN_MARKET_GBPUSD_M15=PENDING
OPEN_MARKET_USDJPY_M15=PENDING
MONDAY_READY=NO
```

Three legitimate current-cycle rejects are acceptable for the market-open proof. A Telegram signal is not required.

## Canonical current sources

1. `CONTINUITY_CURRENT.md`
2. `AI_START_HERE.md`
3. `audits/PRE_MARKET_READINESS_CHECKPOINT_2026-08-09.md`
4. GitHub issue #9
5. this file

`ERRORS.md`, `RESOLVED.md`, and older dated audits preserve historical failure and repair context; current gate truth must follow the sources above when historical wording differs.

## Exactly one next action

Fix every still-valid unresolved PR #89 review finding on branch `fix/watchdog-persistence-guardian-20260809`, run focused validation, and stop for human confirmation before commit/push. Do not mutate the phone/runtime while fixing the GitHub PR.