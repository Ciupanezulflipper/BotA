# BotA Errors and Silent-Failure Register

Last updated: **2026-08-13**

Purpose: preserve verified failure classes, current open risks, fixed solutions, and prevention rules without letting old snapshots masquerade as current production truth.

Canonical current sources:

- `CONTINUITY_CURRENT.md`
- `AI_START_HERE.md`
- `CHAT_HANDOFF_BOTA.md`
- `audits/READ_ONLY_ADVERSARIAL_AUDIT_2026-08-13.md`
- GitHub issue #9
- PR #108 exact-head CI/review state
- verified phone/runtime evidence when current production claims are required

## Current verdict

```text
PRE_AUDIT_RUNTIME_CODE_MAIN=3e69920582d3d310be751e7b451f1afb67e1e5bb
POST_PLACEHOLDER_REVERT_MAIN=3cf3dd1470e4dff7ec4e4d4d7b32f8eb57e9c022
CONTENT_DIFF_3e699205_TO_3cf3dd14=ZERO_FILES
PR108_HEAD=bf30cfcba7af7d22a963d799809b8c7b1f47809d
PR108_STATE=OPEN_DRAFT
PR108_CI_GREEN=NO
PR108_REVIEWED=NO
PR108_DEPLOYABLE=NO
PR102_DO_NOT_DEPLOY=YES
CURRENT_VALID_PR108_PHONE_PACKAGE=NO
PHONE_ACTION=NO
```

PR #89 is merged and no longer the current blocker. The active blocker is PR #108 corrective closure. Historical phone PASS evidence remains valid as historical evidence only; current phone health was not reverified by the 2026-08-13 repository audit.

## E001 — Scope branching / mixed phases

**Failure:** repository, runtime, documentation, deployment, and strategy work were mixed.

**Prevention:** one phase/evidence domain/acceptance gate per package; keep current-state files synchronized; keep dated audits immutable.

## E002 — Repository state mistaken for deployed runtime

**Failure:** GitHub `main`, a merged PR, or phone checkout HEAD treated as proof of the live release.

**Prevention:** track `code-ready -> reviewed -> merged -> deployable -> deployed -> runtime-verified -> live-path-verified` separately.

## E003 — Duplicate execution ownership

**Failure:** cron, runit, boot launchers, wrappers, or multiple supervisors can own the same job.

**Historical watcher rule:** runit-only; direct watcher cron count `0`.

**Prevention:** prove one owner at the current gate, not only historically.

## E004 — Dead manager / orphaned service topology

**Failure:** `runsv` supervisors can survive manager loss and become PID-1 orphans while services continue running.

**Historical verified recovery:** one manager, `owned=7/7`, `running=7/7`, `orphaned=0`, duplicates `0`.

**Prevention:** service liveness is insufficient without supervisor lineage/ownership.

## E005 — Device wall-clock leakage into trading semantics

**Failure:** Android wall clock differed from trusted server time while nested strategy/event paths used local wall time.

**Resolved historical package:** scorer/session/calendar/news event-time semantics were bound to inherited trusted epoch; monotonic/BOOTTIME remained elapsed-time domain.

## E006 — Partial pair observability

**Failure:** health can falsely pass while USDJPY disappears.

**Prevention:** require current-cycle EURUSD/GBPUSD/USDJPY M15 observability together.

## E007 — Pre-journal dedup / lost decision evidence

**Failure:** delivery/dedup interfered with complete decision journaling.

**Prevention:** journal evaluation independently from delivery/dedup state.

## E008 — Inner watcher failure hidden by semantic aggregation

**Failure:** partial semantic evidence can look healthy while current inner execution failed.

**Prevention:** nonzero execution failure dominates semantic aggregation.

## E009 — Watcher cycle without terminal outcome

**Failure:** liveness without an authoritative terminal event.

**Prevention:** coherent cycle ID + append-only evidence + one authoritative terminal outcome.

## E010 — Moving GitHub release target during deployment

**Failure:** deployment uses branch state while `main` moves.

**Prevention:** immutable commit/object pin plus final remote-pin check immediately before mutation.

## E011 — Non-executable runit wrapper

**Failure:** correct content with wrong executable mode blocked activation.

**Prevention:** deployment parity includes bytes and mode.

## E012 — Wrong service-root assumption

**Failure:** tooling assumed the wrong Termux service root.

**Prevention:** resolve canonical service tree and wrapper physical path explicitly.

## E013 — Deployment manifest drift

**Failure:** generated deployment package omits audited files or includes unrelated files.

**Prevention:** exact manifest, immutable source verification, expected file count, explicit config changes only.

## E014 — ProfitLab cursor replay risk

**Failure:** bootstrap/reset can replay historical alert rows.

**Prevention:** preserve cursor; do not bootstrap current production without explicit separate approval.

## E015 — Persisted compact-state schema label lag

**Observation:** compact state may retain older schema labels while newer events use a newer event schema.

**Classification:** bookkeeping debt unless behavior is affected.

## E016 — Stale event mistaken for current failure

**Failure:** old failures in compact state can be read as current.

**Prevention:** compare timestamps/cycle IDs against deployment and require fresh evidence.

## E017 — Stale overlapping PRs

**Failure:** old-base PRs can look actionable after architecture/runtime changes.

**Current containment:** stale PR #7 must not be merged wholesale; PR #102 is now also superseded for the PR #108 corrective path.

## E018 — Calendar before/after exclusion-window sign inversion

**Failure:** signed event distance was paired with reversed asymmetric window comparisons.

**Resolved historical package:** positive distance = before event; negative distance = after event, with boundary tests.

## E019 — Nested components established inconsistent cycle time

**Failure:** outer gate and nested components could establish different `now` values.

**Resolved historical package:** inherited `BOTA_SERVER_EPOCH` reused through audited strategy/event-time path.

## E020 — Stale live singleton daemon blocked manager-owned service

**Failure:** old PID-1-owned `crond` held the pidfile while current manager-owned runsv retried replacements.

**Historical repair:** identity-check stale daemon, quiesce failed loop, terminate only corroborated stale daemon, verify manager-owned replacement.

## E021 — Health gate checked service liveness without owner lineage

**Failure:** `running=7/7` could coexist with PID-1 orphan supervisors.

**Prevention:** require manager count, supervisor lineage, duplicate count, service liveness, and singleton-child ownership.

## E022 — Watchdog source existed while persistent startup was unproven

**Failure:** source parity was mistaken for persistent recovery proof.

**Historical resolution:** managed boot persistence and watchdog singleton were later proven.

## E023 — Watchdog-liveness guardian was once the current blocker

**Historical state:** PR #89 previously blocked readiness.

**Current correction:** PR #89 was merged on 2026-08-09. Any handoff still calling PR #89 the current blocker is stale.

**Current blocker:** PR #108 corrective integration closure.

## E024 — False-green security workflow

**Failure:** a workflow labeled Security Scan can be green even while scanners found issues because commands intentionally swallow nonzero exit status.

**Proven 2026-08-13:**

- ShellCheck command uses `|| true`.
- Bandit command uses `|| true`.

**Impact:** `Security Scan=PASS` does not prove ShellCheck/Bandit clean.

**Prevention:** if a scanner is claimed as a gate, its unacceptable findings must propagate nonzero status to the workflow. Advisory scans must be explicitly labeled advisory and must not be used as readiness evidence.

**Status:** OPEN / PR #108 blocker.

## E025 — Gitleaks sensitive-path blind spot

**Failure:** Gitleaks can report clean while the configuration globally excludes the exact path classes most likely to contain credentials.

**Proven 2026-08-13:** current `.gitleaks.toml` globally allowlists `.env*`, `config/tele.env`, `config.backup-*`, `_snapshots/`, and `archive/` classes.

**Impact:** green Gitleaks is insufficient proof for those excluded classes.

**Credential caution:** the audit does not prove whether historical credentials are currently valid or already rotated/revoked.

**Prevention:** narrow allowlists to explicit samples/placeholders/tests; scan current sensitive working-tree classes with a blocking configuration; treat history remediation/rotation as separate evidence.

**Status:** OPEN / PR #108 blocker.

## E026 — Provider-limit nested-default aliasing

**Failure:** `DEFAULTS.copy()` is shallow. On cold start, `stamp()` can obtain a nested dictionary aliased to the module-level `DEFAULTS` object and mutate default cooldown state process-wide.

**Proven 2026-08-13:** defect exists on current runtime-code baseline.

**Candidate narrow fix:** deep-copy defaults and copy selected provider entry before mutation; add regression proving module defaults remain unchanged.

**Scope rule:** use the focused defect fix only; do not merge PR #104 wholesale.

**Status:** OPEN / PR #108 corrective scope.

## E027 — Deployment package superseded by newer corrective runtime

**Failure:** a reviewed/open deployment package can outlive the runtime generation it was designed to deploy and appear actionable.

**Proven 2026-08-13:** PR #102 is open/draft and pinned to the older PR #101/#103 generation, while PR #108 explicitly requires a new deployment package after final corrective merge.

**Prevention:** deployment authority is SHA/generation-specific and expires when the target runtime changes materially.

```text
PR102_DO_NOT_DEPLOY=YES
CURRENT_VALID_PR108_PHONE_PACKAGE=NO
```

**Status:** OPEN operational guard; no phone action.

## E028 — Documentation write accidentally targeted protected main

**Failure:** during 2026-08-13 audit recording, a placeholder audit file was mistakenly created on protected `main` before the intended docs branch existed.

**Containment:** placeholder was immediately deleted. Protected branch refused force reset, so the create+revert pair remains in history.

**Verification:** direct compare from pre-write `3e699205...` to post-revert `3cf3dd14...` reports zero changed files.

**Impact:** no runtime/strategy content drift; Git history contains two documentation-only commits.

**Prevention:** create/verify target branch before any content write; reject writes when branch is missing rather than falling back to default branch.

**Status:** RESOLVED / recorded for recurrence prevention.

## Current open risks

```text
PR108_EXACT_HEAD_CI=FAIL
PR108_REVIEW_COMPLETE=NO
SONARCLOUD_SECURITY_RATING_NEW_CODE=D
SECURITY_WORKFLOW_FALSE_GREEN_CLASS=OPEN
GITLEAKS_SENSITIVE_PATH_BLIND_SPOT=OPEN
PROVIDER_LIMITS_ALIASING=OPEN
HISTORICAL_CREDENTIAL_ROTATION_STATUS=UNPROVEN
PR102_SUPERSEDED_DO_NOT_DEPLOY=YES
CURRENT_VALID_PR108_PHONE_PACKAGE=NO
CURRENT_PHONE_HEALTH=NOT_REVERIFIED_BY_2026_08_13_AUDIT
OPEN_MARKET_THREE_PAIR_PROOF_FOR_FINAL_CORRECTIVE_RUNTIME=PENDING
SIGNAL_CLOSER_LIFECYCLE=SEPARATE_WORK
MONDAY_READY=NO
```

## Exactly one next engineering action

Close PR #108 in the repository only: make security gates truthful, remove Gitleaks blind spots, resolve Sonar/DeepSource/current review findings, integrate only narrow validated fixes from PRs #104-#106, keep PR #107 out of the reliability freeze, prove no strategy/config drift, and obtain exact-head CI plus actual current-head review PASS.

Do not mutate the phone until a new reviewed rollback-capable deployment package is built from the final merged corrective runtime commit.
