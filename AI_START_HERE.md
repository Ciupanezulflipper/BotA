# BotA AI Start Here

Last updated: **2026-08-13**

Read this before proposing BotA commands, code, service, strategy, Telegram, provider, Supabase, replay, deployment, or Android/Termux changes.

## Evidence hierarchy

1. current BotA GitHub repository state;
2. current PR/CI/review state;
3. verified phone/runtime evidence when runtime claims are required;
4. dated audits and continuity files for navigation/history only.

Never let a dated handoff silently override newer live GitHub or phone evidence.

## Current repository truth

```text
PRE_AUDIT_RUNTIME_CODE_MAIN=3e69920582d3d310be751e7b451f1afb67e1e5bb
POST_PLACEHOLDER_REVERT_MAIN=3cf3dd1470e4dff7ec4e4d4d7b32f8eb57e9c022
CONTENT_DIFF_3e699205_TO_3cf3dd14=ZERO_FILES
PR108_HEAD=bf30cfcba7af7d22a963d799809b8c7b1f47809d
PR108_STATE=OPEN
PR108_DRAFT=YES
PR108_DEPLOYABLE=NO
PHONE_ACTION=NO
```

The two commits after `3e699205...` are a documentation placeholder create+revert pair. Protected `main` rejected a force reset; direct compare proves zero changed files between `3e699205...` and `3cf3dd14...`.

## Stable production scope

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
```

No reliability/readiness fix may manufacture activity by weakening strategy gates.

## Historical phone baseline that was previously proven

The last recorded closed-market production evidence proved:

```text
SINGLE_NATIVE_MANAGER=PASS
REQUIRED_SERVICES_OWNED=7/7
REQUIRED_SERVICES_RUNNING=7/7
ORPHANED_RUNSV=0
DUPLICATE_SERVICE_ROWS=0
WATCHDOG_SINGLETON=PASS
BOOT_PERSISTENCE=PASS
CRON_OWNERSHIP=PASS
TRUSTED_CLOCK=PASS
PRE_MARKET_INTEGRITY=PASS
```

These are historical verified phone facts, not a claim about the phone's current state on 2026-08-13. Reverify the phone before making a current runtime-health claim.

## Current blocker: PR #108 corrective closure

PR #89 is merged and is no longer the current blocker.

PR #108 (`fix: reconcile Devin findings and enforce predeploy runtime evidence contracts`) is the active corrective integration package. It is intentionally draft and explicitly not deployable.

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

## Proven blockers from the 2026-08-13 adversarial audit

1. PR #108 exact-head CI is not green: DeepSource Python FAIL, DeepSource Shell FAIL, SonarCloud quality gate FAIL, Security Rating on New Code D.
2. CodeRabbit has not completed a current-head content review because PR #108 is draft.
3. `.github/workflows/security.yml` allows ShellCheck and Bandit commands to succeed despite findings via `|| true`; therefore a green Security Scan does not prove those tools clean.
4. `.gitleaks.toml` still globally allowlists sensitive path classes including `.env*`, `config/tele.env`, backup directories, `_snapshots/`, and `archive/`; therefore green Gitleaks does not prove those classes secret-free.
5. `tools/provider_limits.py` still contains a shallow-copy aliasing defect (`DEFAULTS.copy()` plus nested mutation) on the cold-start path.
6. PR #102 is superseded for the current corrective path and must not be deployed.
7. The generation-barrier regression is now explicitly invoked by the PR #108 provider/pipeline CI workflow; this is a proven positive control.

Canonical audit: `audits/READ_ONLY_ADVERSARIAL_AUDIT_2026-08-13.md`.

## Security truth

Do not claim historical credentials are valid, invalid, rotated, or revoked without independent evidence.

Current status:

```text
HISTORICAL_CREDENTIAL_ROTATION=UNPROVEN
GITLEAKS_SENSITIVE_PATH_BLIND_SPOT=OPEN
SECURITY_WORKFLOW_FALSE_GREEN_CLASS=OPEN
SONARCLOUD_SECURITY_GATE=FAIL
```

## Deployment truth

PR #102 is open/draft but pinned to the older PR #101/#103 generation. PR #108 requires a new transactional deployment package only after the final corrective runtime commit is merged and reviewed.

```text
PR102_DO_NOT_DEPLOY=YES
CURRENT_VALID_PR108_PHONE_PACKAGE=NO
PHONE_ACTION=NO
```

## Mandatory operating model

```text
GitHub PR -> code/review/CI/documentation
Phone      -> runtime evidence + explicitly approved deployment only
```

Track separately:

```text
code-ready -> reviewed -> merged -> deployable -> deployed -> runtime-verified -> live-path-verified
```

Never collapse those stages into one "ready" claim.

## Read first

1. `CONTINUITY_CURRENT.md`
2. `audits/READ_ONLY_ADVERSARIAL_AUDIT_2026-08-13.md`
3. GitHub issue #9
4. PR #108 and its exact-head checks/review threads
5. `ERRORS.md`
6. `RESOLVED.md`
7. verified phone/runtime evidence when current production state is required

## Exactly one next engineering action

Close the PR #108 repository-only corrective package: make security gates truthful/blocking, remove Gitleaks sensitive-path blind spots, resolve Sonar/DeepSource/review findings, integrate only independently validated narrow fixes from PRs #104-#106, keep PR #107 broad refactor outside the reliability freeze, prove no strategy/config drift, and obtain exact-head CI plus real current-head review PASS.

Do **not** mutate the Android/Termux runtime until that repository gate is complete and a new reviewed rollback-capable deployment package is built from the final merged corrective runtime commit.
