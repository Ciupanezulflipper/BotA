# BotA Read-Only Adversarial Audit — 2026-08-13

Status: **BLOCKED**

Scope: repository/readiness/security/evidence audit only. No phone, runtime, strategy, provider, Telegram, Supabase, or deployment mutation was performed.

## Repository provenance

The verified BotA runtime/code baseline at the start of this audit was:

```text
PRE_AUDIT_MAIN=3e69920582d3d310be751e7b451f1afb67e1e5bb
```

During documentation recording, an accidental placeholder-only commit was created on protected `main` and immediately reverted. GitHub refused a force reset, so the create+revert pair remains in history. A direct compare from `3e699205...` to the post-revert `main` showed **zero changed files**.

```text
POST_REVERT_MAIN=3cf3dd1470e4dff7ec4e4d4d7b32f8eb57e9c022
COMPARE_FILES_CHANGED=0
RUNTIME_OR_STRATEGY_CONTENT_DRIFT_FROM_3e699205=NONE
```

All intended audit/handoff changes after that correction are isolated on a documentation branch.

## Authoritative live repository state at audit time

```text
RUNTIME_CODE_BASELINE=3e69920582d3d310be751e7b451f1afb67e1e5bb
PR108_HEAD=bf30cfcba7af7d22a963d799809b8c7b1f47809d
PR108_STATE=OPEN
PR108_DRAFT=YES
PR108_DEPLOYABLE=NO
PHONE_ACTION=NO
```

PR #108 is the current corrective integration PR. Its own contract says `DRAFT / NOT DEPLOYABLE / PHONE ACTION = NO`.

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

## Proven findings

### F108-01 — Exact-head CI is not green

At PR #108 head `bf30cfcba7af7d22a963d799809b8c7b1f47809d`:

- DeepSource Python: FAIL
- DeepSource Shell: FAIL
- SonarCloud quality gate: FAIL
- SonarCloud Security Rating on New Code: D
- CodeRabbit did not provide a complete current-head content review because the PR is draft.

Result: PR #108 cannot be represented as reviewed, CI-clean, or deployable.

### F108-02 — Security workflow contains false-green behavior

Current `.github/workflows/security.yml`:

- ShellCheck uses `|| true`, so findings do not fail the job.
- Bandit uses `|| true`, so findings do not fail the job.

Therefore a green Security Scan does not prove ShellCheck/Bandit clean.

This is a recurrence of the failure class `green check != enforced invariant`.

### F108-03 — Gitleaks path allowlist still hides sensitive path classes

Current `.gitleaks.toml` globally allowlists sensitive path classes including:

- `.env`
- `.env.*`
- `.env.runtime`
- `.env.profitlab`
- `.env.botA*`
- `config/tele.env`
- `config.backup-*`
- `_snapshots/`
- `archive/`

This reproduces the exact blind-spot class reported by PR #106. A green Gitleaks result under this configuration is insufficient evidence that those path classes are secret-free.

No claim is made here that any historical credential is currently valid. Credential validity/rotation remains unproven until independently verified.

### F108-04 — `provider_limits` shallow-copy aliasing defect exists on `main`

Current `tools/provider_limits.py` returns `DEFAULTS.copy()` on cold start and then mutates nested provider entries in `stamp()`.

Because `dict.copy()` is shallow, a nested provider dictionary can alias `DEFAULTS`, allowing process-wide default cooldown values to be mutated.

PR #104 proposes a focused deep-copy correction and regression. That fix is useful, but PR #104 must not be merged wholesale into the reliability freeze.

### F108-05 — Generation-barrier regression is now actually invoked by CI

The PR #108 provider/pipeline workflow explicitly runs:

```text
tests.test_runtime_deployment_barrier
```

This closes the prior gap where a barrier test could exist without being executed by the required CI path.

Status: PROVEN POSITIVE CONTROL.

### F108-06 — PR #102 is superseded and must not be deployed

PR #102 remains open/draft and is pinned to the older PR #101/#103 runtime generation.

PR #108 explicitly requires a separate new transactional Android deployment package only after the final corrective runtime commit is merged and reviewed.

Therefore:

```text
PR102_DEPLOYMENT_AUTHORITY=REVOKED_FOR_CURRENT_CORRECTIVE_PATH
PR102_DO_NOT_DEPLOY=YES
```

### F108-07 — Issue #9 and continuity files were stale

Issue #9 and the repository handoff files still encoded PR #89 as the current blocker even though PR #89 was merged on 2026-08-09.

This is a direct instance of:

- stale documentation presented as live truth;
- repository state confused with deployed state.

The current blocker is PR #108 corrective closure, not PR #89.

## Unproven / must not be claimed

```text
ALL_DEVIN_FINDINGS_RECONCILED=UNPROVEN
CURRENT_HEAD_CODERABBIT_CONTENT_REVIEW=UNPROVEN
SONAR_SECURITY_GATE_CLEAN=FALSE
HISTORICAL_CREDENTIALS_ROTATED_OR_REVOKED=UNPROVEN
FINAL_PR108_STRATEGY_CONFIG_DRIFT_ZERO=UNPROVEN
CURRENT_PHONE_TOPOLOGY_HEALTH=UNPROVEN_IN_THIS_AUDIT
PR108_DEPLOYED=NO
PR108_RUNTIME_VERIFIED=NO
PR108_LIVE_THREE_PAIR_PATH_VERIFIED=NO
PR108_TELEGRAM_SUPABASE_E2E_EVIDENCE_VERIFIED=NO
```

## Current required corrective package

The next repository-only package must:

1. make intended security gates truthful and blocking;
2. remove inappropriate Gitleaks sensitive-path blind spots;
3. resolve SonarCloud Security Rating D and exact-head quality-gate failure;
4. integrate only the independently validated `provider_limits` aliasing fix from PR #104 with focused regression coverage;
5. reconcile only proven relevant findings from PRs #105/#106;
6. keep PR #107 broad utility refactor outside the reliability freeze unless a specific defect requires a minimal extraction;
7. resolve current delivery/evidence/analyzer findings;
8. independently prove no strategy/config drift;
9. obtain an actual current-head review after the PR is reviewable;
10. rerun all required exact-head gates.

Only after the final corrective runtime commit is merged should a new rollback-capable Android deployment package be built and reviewed.

## Acceptance criteria

```text
EXACT_HEAD_CI_GREEN=REQUIRED
DEEPSOURCE_PYTHON=PASS_REQUIRED
DEEPSOURCE_SHELL=PASS_REQUIRED
SONARCLOUD_SECURITY_GATE=PASS_REQUIRED
GITLEAKS_SENSITIVE_PATH_BLIND_SPOT=REMOVED_REQUIRED
SHELLCHECK_BLOCKING=REQUIRED_IF_GATE_IS_CLAIMED
BANDIT_BLOCKING=REQUIRED_IF_GATE_IS_CLAIMED
PROVIDER_LIMITS_ALIAS_REGRESSION=PASS_REQUIRED
GENERATION_BARRIER_TEST_EXECUTED=PASS_REQUIRED
CURRENT_RELIABILITY_SECURITY_FINDINGS=RESOLVED_OR_EVIDENCE_DISPROVEN
CURRENT_HEAD_REVIEW=COMPLETED_REQUIRED
STRATEGY_CONFIG_DRIFT=NONE_REQUIRED
ANDROID_DEPLOYMENT_AUTHORIZED=NO_UNTIL_ALL_ABOVE_PASS
```

## Final verdict

```text
STATUS=BLOCKED
TESTS_PASSED=FALSE
DEPLOYABLE=FALSE
HUMAN_REVIEW_REQUIRED=TRUE
PHONE_ACTION=NO
```
