# BotA Errors and Silent-Failure Register

Last updated: **2026-08-09 UTC**

Purpose: preserve verified failure classes, current open risks, fixed solutions, and prevention rules without letting old snapshots masquerade as current production truth.

Canonical current sources:

- `CONTINUITY_CURRENT.md`
- `AI_START_HERE.md`
- `CHAT_HANDOFF_BOTA.md`
- `audits/PRE_MARKET_READINESS_CHECKPOINT_2026-08-09.md`
- `audits/ERROR_LOG.md`
- GitHub issue #9

## Current verdict

```text
PHONE_RUNTIME_SOURCE_BASELINE=5cbfbf11fd98d9a40b1d5ea28995f584ec9da080
PACKAGE_1_CLOCK_SESSION=PASS
PACKAGE_2_CONTROL_PLANE_RECOVERY=PASS
PACKAGE_2_FINALIZER_DEPLOY=PASS
PR87_PR88_PHONE_DEPLOY=PASS
RUNTIME_DEPENDENCY_CONTRACT=PASS
CURRENT_CONTROL_PLANE=HEALTHY
CURRENT_OWNED_SERVICES=7/7
CURRENT_RUNNING_SERVICES=7/7
CURRENT_ORPHANED_RUNSV=0
CURRENT_DUPLICATE_SERVICE_ROWS=0
WATCHDOG_SINGLETON=PASS
BOOT_PERSISTENCE=PASS
PROFITLAB_CURSOR=PRESERVED
NATURAL_SHADOW_CYCLE=PASS
PRE_MARKET_PRODUCTION_INTEGRITY=PASS
PR89_WATCHDOG_GUARDIAN=BLOCKED_REVIEW_AND_CI
OPEN_MARKET_THREE_PAIR_LIVE_PROOF=PENDING
MONDAY_READY=NO
```

Package #1 and Package #2 closed-market infrastructure are deployed and proven. The active blocker is the separate PR #89 watchdog-liveness guardian plus the later genuine market-open three-pair proof.

## E001 — Scope branching / mixed phases

**Failure:** repository, runtime, documentation, deployment, and strategy work were mixed.

**Prevention:** one phase/evidence domain/acceptance gate per package; keep current-state files synchronized; keep dated audits immutable.

## E002 — Repository state mistaken for deployed runtime

**Failure:** GitHub `main` or phone checkout HEAD treated as proof of the live release.

**Prevention:** immutable approved SHA + deployed blob/mode parity + active-wrapper parity + runtime config + live evidence.

## E003 — Duplicate execution ownership

**Failure:** cron, runit, boot launchers, wrappers, or multiple supervisors can own the same job.

**Current watcher rule:** runit-only; direct watcher cron count `0`.

**Prevention:** prove one owner at the current gate, not only historically.

## E004 — Dead manager / orphaned service topology

**Failure:** `runsv` supervisors can survive manager loss and become PID-1 orphans while services continue running.

**Observed during Package #2:** live services remained while manager ownership was split or absent.

**Final verified state:**

```text
manager_count=1
owned=7/7
running=7/7
orphaned=0
duplicate_service_rows=0
```

**Status:** core recovery/finalizer path deployed and pre-market gate PASS. Independent watchdog-liveness after unexpected watchdog death is tracked separately in PR #89.

## E005 — Device wall-clock leakage into trading semantics

**Failure:** Android wall clock was about one hour behind trusted server UTC and nested strategy/event paths still used local wall time.

**Package #1 fixes:** scorer session component, nested market-gate reuse, economic-calendar timing, and active Finnhub calendar-date selection now derive from trusted epoch. CLOCK_BOOTTIME/monotonic remains for elapsed-time health/cooldown.

**Live proof:** Package #1 terminal event persisted `time_source=server_epoch`.

**Residual risk:** wall-clock cron scheduling remains a separate operational/device concern.

## E006 — Partial pair observability

**Failure:** health can falsely pass while USDJPY disappears.

**Current fix:** three-pair EURUSD/GBPUSD/USDJPY M15 observability contract.

**Remaining proof:** genuine open-market same-cycle decisions for all three pairs.

## E007 — Pre-journal dedup / lost decision evidence

**Failure:** delivery/dedup previously interfered with complete decision journaling.

**Prevention:** persist decisions independently from delivery/dedup state; Telegram delivery is not evaluation proof.

## E008 — Inner watcher failure hidden by semantic aggregation

**Failure:** existing/partial semantic evidence can look healthy while current inner execution failed.

**Fix:** nonzero inner execution dominates semantic aggregation and surfaces an operational terminal failure.

## E009 — Watcher cycle without terminal outcome

**Failure:** process/heartbeat liveness while a watcher cycle disappears without a terminal record.

**Fix:** gated cycle + coherent cycle ID + append-only ledger + authoritative terminal outcome.

## E010 — Moving GitHub release target during deployment

**Failure:** deploy against branch state while `main` moves.

**Containment:** release-pin mismatch caused safe pre-mutation abort.

**Prevention:** immutable commit pin plus final remote-pin check immediately before mutation.

## E011 — Non-executable runit wrapper

**Failure:** correct contents stored with Git mode `100644` made watcher activation fail.

**Fix:** PR #81 changed `ops/runit/bota-watcher.run` to `100755`; deployment rollback preserved prior runtime until corrected.

## E012 — Wrong service-root assumption

**Failure:** tooling assumed every service lived under `${HOME}/.config/bota-sv`.

**Fix:** canonical service tree is `$PREFIX/var/service`; resolve the watcher wrapper physical path separately.

## E013 — Deployment manifest drift

**Failure:** generated deployment instructions can omit audited files or include unrelated files.

**Prevention:** exact parity-audited manifest, expected file count, immutable source verification, explicit phone config changes only.

## E014 — ProfitLab cursor replay risk

**Failure:** bootstrap/reset could replay historical alert rows.

**Current state:** preserved through PR #87/#88 deployment and pre-market gate.

**Prevention:** preserve cursor; do not run `--bootstrap` on current production.

## E015 — Persisted compact-state schema label lag

**Observation:** compact state may retain an older top-level schema label while current events use schema 1.1.

**Classification:** bookkeeping debt unless behavior is affected.

## E016 — Stale event mistaken for current failure

**Observation:** an older shadow failure can remain in compact state after deployment.

**Prevention:** compare timestamp/cycle against deployment and require fresh updater/shadow evidence. A natural post-deploy shadow cycle now passes; the same principle remains required for the market-open gate.

## E017 — Stale overlapping PRs

**Failure:** old-base PRs can look actionable after architecture moves.

**Containment:** PR #77 closed unmerged; stale draft PR #7 must not be merged wholesale.

## E018 — Calendar before/after exclusion-window sign inversion

**Failure:** `minutes_away = event - now` was paired with reversed before/after comparisons, so configured asymmetric windows were applied in the wrong direction.

**Package #1 fix:** positive `minutes_away` is treated as before-event; negative as after-event. Boundary tests cover HIGH and MEDIUM windows on both sides.

## E019 — Nested components established inconsistent cycle time

**Failure:** outer gate could use trusted server time while nested scorer/gates independently re-probed or read another clock.

**Package #1 fix:** inherited `BOTA_SERVER_EPOCH` is reused through the audited strategy/event-time path.

## E020 — Stale live singleton daemon blocked manager-owned service

**Failure:** current runit reported `crond` down while an old live PID-1-owned `crond` still executed jobs and held `/var/run/crond.pid`.

**Live repair:** identity-check stale daemon -> quiesce failed restart loop -> terminate only stale daemon -> manager-owned runsv starts replacement -> verify one stable live `crond`.

**Status:** resolved in live incident and incorporated into reviewed Package #2 hardening; current pre-market cron ownership PASS.

## E021 — Health gate checked service liveness without owner lineage

**Failure:** seven services could all report `run` while supervisors were PID-1 orphans.

**Fix:** production health now requires manager count, supervisor lineage, duplicate count, service liveness, and singleton child ownership where applicable.

**Current proof:** `owned=7/7`, `running=7/7`, `orphaned=0`, duplicates `0`.

## E022 — Watchdog source existed while persistent startup was unproven

**Historical failure:** watchdog source files matched GitHub, but persistent startup had not yet been finalized/proven.

**Resolution:** Package #2 finalizer and managed Termux:Boot watchdog block are deployed; one watchdog process holds the watchdog lock; `CHECK_BOOT_PERSISTENCE=PASS` and `CHECK_WATCHDOG_OWNERSHIP=PASS` in the corrected pre-market gate.

**Status:** RESOLVED for boot persistence.

## E023 — Independent watchdog-liveness guardian still review-blocked

**Failure class being addressed:** the watchdog can disappear after boot while `crond` survives. A one-shot boot launcher alone does not guarantee watchdog liveness for the rest of the boot.

**PR #89 design:** a narrow once-per-minute cron guardian may invoke only the already-reviewed watchdog launcher when the watchdog is exactly absent and lock ownership is unambiguous. It must never signal services or reconcile topology itself.

**Current PR #89 state:**

```text
HEAD=4f73a999634bc83c52defb0d31bfb72291ac83b9
STATE=OPEN
MERGEABLE=true
GITHUB_ACTIONS_SECURITY_SCAN=PASS
GITHUB_ACTIONS_NATIVE_WATCHDOG_GUARDIAN=PASS
DEEPSOURCE_PYTHON=FAIL
UNRESOLVED_REVIEW_THREADS=10
DISTINCT_REMEDIATION_ITEMS=9
```

Two unresolved threads report the same unused-variable cleanup; the current connector view therefore contains 10 open threads representing 9 distinct fixes.

Still-valid review requirements:

1. active advisory `FLOCK` ownership, not open-descriptor inference;
2. shell-safe path quoting and CR/LF rejection in rendered cron;
3. controlled status/RC when event logging itself fails;
4. AST-based no-termination validation plus negative fixtures;
5. complete rendered-crontab validation and exactly one active managed `--ensure` guardian line;
6. reject non-finite timeout values;
7. disable checkout credential persistence;
8. unused-value cleanup;
9. staticmethod cleanup in tests.

**Prevention:** do not deploy PR #89 until exact-head review/static/CI gates pass and phone fault injection proves watchdog-only termination is repaired by exactly one guardian-driven watchdog recreation.

## Package #1 fixed-solution summary

```text
TRUSTED_TIME_HELPER=DEPLOYED
MARKET_GATE_TRUSTED_EPOCH=DEPLOYED
SESSION_SCORE_TRUSTED_EPOCH=DEPLOYED
CALENDAR_WINDOW_FIX=DEPLOYED
NEWS_DATE_TRUSTED_EPOCH=DEPLOYED
RUNTIME_PARITY=PASS
LIVE_PROOF=PASS
THRESHOLDS_CHANGED=NO
PAIR_SCOPE_CHANGED=NO
```

## Package #2 fixed-solution summary

```text
CONTROL_PLANE_RECOVERY=PASS
FINALIZER_DEPLOY=PASS
BOOT_PERSISTENCE=PASS
WATCHDOG_SINGLETON=PASS
PR87_PR88_PHONE_DEPLOY=PASS
RUNTIME_DEPENDENCY_CONTRACT=PASS
NATURAL_SHADOW_CYCLE=PASS
PRE_MARKET_PRODUCTION_INTEGRITY=PASS
PROFITLAB_PRESERVED=PASS
STRATEGY_CHANGED=NO
```

## Historical strategy-quality evidence remains separate

The June-July replay/outcome evidence remains preserved. Current readiness is an operational proof problem; missing runtime evidence must never be “fixed” by lowering thresholds.

## Current open risks

```text
PR89_WATCHDOG_LIVENESS_GUARDIAN=BLOCKED_REVIEW_AND_CI
ANDROID_WALL_CLOCK_CRON_SCHEDULING=OPEN_WARN
OPEN_MARKET_THREE_PAIR_PROOF=PENDING
SIGNAL_CLOSER_LIFECYCLE=SEPARATE_WORK
H1_ADX_OVERRIDE_CONTRACT=SEPARATE_APPROVAL
COMPACT_STATE_SCHEMA_NORMALIZATION=DEFERRED
MONDAY_READY=NO
```

## Exactly one next engineering action

Fix every still-valid unresolved PR #89 review finding on `fix/watchdog-persistence-guardian-20260809`, run focused validation, and stop for human confirmation before commit/push. Do not mutate the phone while fixing the GitHub PR.