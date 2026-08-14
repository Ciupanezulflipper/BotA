# BotA Chat Handoff

Last updated: **2026-08-13**

Read this first in any new AI session before proposing BotA changes.

## Current grounded answer

```text
PRE_AUDIT_RUNTIME_CODE_MAIN=3e69920582d3d310be751e7b451f1afb67e1e5bb
POST_PLACEHOLDER_REVERT_MAIN=3cf3dd1470e4dff7ec4e4d4d7b32f8eb57e9c022
CONTENT_DIFF_3e699205_TO_3cf3dd14=ZERO_FILES
PR108_HEAD=bf30cfcba7af7d22a963d799809b8c7b1f47809d
PR108_STATE=OPEN
PR108_DRAFT=YES
PR108_CI_GREEN=NO
PR108_REVIEWED=NO
PR108_DEPLOYABLE=NO
PR102_DO_NOT_DEPLOY=YES
CURRENT_VALID_PR108_PHONE_PACKAGE=NO
PHONE_ACTION=NO
```

The two commits after `3e699205...` are a documentation placeholder create+revert pair. Direct compare reports zero changed files. They do not represent runtime or strategy drift.

## Stable production scope

```text
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
POLICY_B_ENABLED=1
POLICY_B_SCORE_MIN=70
POLICY_B_ADX_MAX=30
TELEGRAM_ENABLED=1
DRY_RUN_MODE=0
```

Do not lower thresholds, expand scope, force signal count, or manufacture Telegram activity to satisfy readiness checks.

## Historical phone evidence

Previously proven phone state included one native manager, 7/7 owned and running required services, zero orphaned `runsv`, zero duplicate service rows, watchdog singleton, boot persistence, cron ownership, trusted-clock PASS, natural shadow-cycle PASS, and corrected pre-market integrity PASS.

Those are retained historical facts. The 2026-08-13 audit was repository-only and did not reverify current phone topology.

## Current blocker — PR #108 corrective closure

PR #89 is merged and is not the current blocker.

PR #108 is explicitly draft/not deployable. At exact head `bf30cfcba7af7d22a963d799809b8c7b1f47809d` the audit proved:

```text
DEEPSOURCE_PYTHON=FAIL
DEEPSOURCE_SHELL=FAIL
SONARCLOUD_QUALITY_GATE=FAIL
SONARCLOUD_SECURITY_RATING_NEW_CODE=D
CODERABBIT_CURRENT_HEAD_CONTENT_REVIEW=NOT_COMPLETED_DRAFT
```

Additional proven findings:

- Security Scan can be false-green because ShellCheck and Bandit use `|| true`.
- Gitleaks still globally allowlists sensitive path classes including `.env*`, `config/tele.env`, backups, `_snapshots/`, and `archive/`.
- Historical credential rotation/revocation is unproven.
- `tools/provider_limits.py` still has shallow-copy nested-default aliasing on the cold-start path.
- `tests.test_runtime_deployment_barrier` is explicitly executed by PR #108 provider/pipeline CI.
- PR #102 is superseded for the current corrective runtime and must not be deployed.

Detailed evidence: `audits/READ_ONLY_ADVERSARIAL_AUDIT_2026-08-13.md`.

## Readiness ladder

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

## Required next package

Repository-only PR #108 corrective closure:

1. make intended security gates blocking and truthful;
2. remove inappropriate Gitleaks sensitive-path blind spots;
3. resolve SonarCloud Security Rating D and quality-gate failure;
4. resolve DeepSource Python/Shell failures;
5. integrate only narrow independently validated fixes from PRs #104-#106;
6. keep PR #107 broad refactor outside the reliability freeze;
7. resolve current evidence/delivery/review findings;
8. independently prove no strategy/config drift;
9. obtain an actual current-head review after the PR is reviewable;
10. rerun exact-head required gates and require PASS.

Only after final merge may a new rollback-capable Android deployment package be built from the final corrective runtime SHA.

## Canonical current sources

1. `CONTINUITY_CURRENT.md`
2. `AI_START_HERE.md`
3. `audits/READ_ONLY_ADVERSARIAL_AUDIT_2026-08-13.md`
4. GitHub issue #9
5. PR #108 exact-head CI/review state
6. verified phone evidence when making current runtime claims
7. this file

## Exactly one next action

Close the PR #108 repository gate. Do not mutate the phone/runtime while that gate is open.
