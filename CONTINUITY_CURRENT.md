# BotA Current Continuity State

Last updated: **2026-08-13**

This file is the current operational handoff. Historical audits and `ERRORS.md` preserve prior incidents; do not reconstruct present production state from older snapshots.

## Current authoritative status

```text
PRE_AUDIT_RUNTIME_CODE_MAIN=3e69920582d3d310be751e7b451f1afb67e1e5bb
POST_PLACEHOLDER_REVERT_MAIN=3cf3dd1470e4dff7ec4e4d4d7b32f8eb57e9c022
CONTENT_DIFF_3e699205_TO_3cf3dd14=ZERO_FILES
PR108_HEAD=bf30cfcba7af7d22a963d799809b8c7b1f47809d
PR108_STATE=OPEN
PR108_DRAFT=YES
PR108_EXACT_HEAD_CI=FAIL
PR108_REVIEW_COMPLETE=NO
PR108_DEPLOYABLE=NO
CURRENT_VALID_PR108_PHONE_PACKAGE=NO
PHONE_ACTION=NO
```

The post-revert `main` is two commits ahead of `3e699205...` only because a documentation placeholder was created accidentally and immediately reverted. GitHub branch protection refused a force reset. Direct compare reports zero changed files, so runtime/strategy content is unchanged from `3e699205...`.

## Stable production scope remains frozen

```text
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
POLICY_B_ENABLED=1
POLICY_B_SCORE_MIN=70
POLICY_B_ADX_MAX=30
TELEGRAM_ENABLED=1
DRY_RUN_MODE=0
DO_NOT_LOWER_THRESHOLDS=YES
DO_NOT_FORCE_SIGNAL_COUNT=YES
DO_NOT_FORCE_TELEGRAM_TEST_SIGNAL=YES
```

## Historical phone proof retained, but not current-state proof

Previously verified phone evidence established:

```text
PACKAGE_1_CLOCK_SESSION=PASS
PACKAGE_2_CONTROL_PLANE_RECOVERY=PASS
PACKAGE_2_FINALIZER_DEPLOY=PASS
PR87_PR88_PHONE_DEPLOY=PASS
RUNTIME_DEPENDENCY_CONTRACT=PASS
NATURAL_SHADOW_CYCLE=PASS
PRE_MARKET_PRODUCTION_INTEGRITY=PASS
MANAGER_COUNT=1
REQUIRED_SERVICES_OWNED=7/7
REQUIRED_SERVICES_RUNNING=7/7
ORPHANED_RUNSV=0
DUPLICATE_SERVICE_ROWS=0
WATCHDOG_SINGLETON=PASS
BOOT_PERSISTENCE=PASS
CRON_OWNERSHIP=PASS
TRUSTED_CLOCK=PASS
```

Those facts are historical evidence. The 2026-08-13 repository audit did not access the phone, so it does not claim the current phone topology is still identical.

## Current blocker: PR #108

PR #89 is merged and no longer blocks readiness.

PR #108 is the current corrective integration package and is explicitly `DRAFT / NOT DEPLOYABLE / PHONE ACTION = NO`.

Current readiness ladder:

```text
CODE_COMPLETE=NO
CI_GREEN=NO
REVIEWED=NO
DEPLOYABLE=NO
DEPLOYED=NO_FOR_PR108
RUNTIME_VERIFIED=NO_FOR_PR108
LIVE_SIGNAL_PATH_VERIFIED=NO_FOR_PR108
EVIDENCE_CAPTURE_VERIFIED_IN_PRODUCTION=NO_FOR_PR108
```

## 2026-08-13 adversarial findings

### Exact-head quality gates

At `PR108_HEAD=bf30cfcba7af7d22a963d799809b8c7b1f47809d`:

```text
DEEPSOURCE_PYTHON=FAIL
DEEPSOURCE_SHELL=FAIL
SONARCLOUD_QUALITY_GATE=FAIL
SONARCLOUD_SECURITY_RATING_NEW_CODE=D
CODERABBIT_CURRENT_HEAD_CONTENT_REVIEW=NOT_COMPLETED_DRAFT
```

### False-green security gate class

Current `.github/workflows/security.yml` runs ShellCheck and Bandit with `|| true`. Therefore a green workflow result does not prove either scanner clean.

Current `.gitleaks.toml` globally allowlists sensitive path classes including `.env*`, `config/tele.env`, `config.backup-*`, `_snapshots/`, and `archive/`. Therefore green Gitleaks under this configuration does not prove those classes secret-free.

Do not claim historical credentials are rotated/revoked unless independently verified.

### Provider limit aliasing defect

`tools/provider_limits.py` still returns `DEFAULTS.copy()` and can mutate nested default provider dictionaries through `stamp()` on the cold-start path. PR #104 contains a proposed deep-copy fix and regression; integrate only the narrow validated fix, not the entire PR.

### Generation-barrier positive control

The PR #108 provider/pipeline workflow explicitly executes `tests.test_runtime_deployment_barrier`. The barrier regression is therefore part of the required CI path.

### Superseded deployment package

PR #102 is open/draft but tied to the older PR #101/#103 generation. It is superseded for the current corrective path.

```text
PR102_DO_NOT_DEPLOY=YES
NEW_PR108_DEPLOYMENT_PACKAGE_REQUIRED_AFTER_FINAL_MERGE=YES
```

## Current freeze

```text
DO_NOT_DEPLOY_PR102=YES
DO_NOT_DEPLOY_PR108=YES
DO_NOT_MUTATE_PHONE=YES
DO_NOT_BOOTSTRAP_PROFITLAB=YES
DO_NOT_LOWER_THRESHOLDS=YES
DO_NOT_FORCE_SIGNAL_COUNT=YES
DO_NOT_FORCE_TELEGRAM_TEST_SIGNAL=YES
DO_NOT_DECLARE_READY_FROM_REPOSITORY_ONLY=YES
```

## Required repository closure before any phone package

1. make intended security checks truly blocking;
2. remove inappropriate Gitleaks sensitive-path blind spots;
3. resolve SonarCloud Security Rating D and quality-gate failure;
4. resolve DeepSource Python/Shell failures;
5. integrate only narrow independently validated fixes from PRs #104-#106;
6. keep PR #107 broad shared-utility refactor outside the reliability freeze unless a specific defect proves a minimal extraction necessary;
7. resolve all current delivery/evidence/review findings;
8. independently prove `STRATEGY_CONFIG_DRIFT=NONE`;
9. obtain a real current-head review after PR #108 is reviewable;
10. rerun exact-head required gates and require PASS.

Only then build a new rollback-capable Android deployment package pinned to the final merged corrective runtime commit.

## Exactly one next engineering action

Complete the PR #108 corrective closure package in GitHub only. Do not touch the phone/runtime while this gate is open.

Canonical detailed evidence: `audits/READ_ONLY_ADVERSARIAL_AUDIT_2026-08-13.md`.
