# BotA Errors and Silent-Failure Register

Last updated: **2026-08-09 UTC**

Purpose: preserve verified failure classes, current open risks, fixed solutions, and prevention rules without letting old snapshots masquerade as current production truth.

Canonical current sources:

- `CONTINUITY_CURRENT.md`
- `AI_START_HERE.md`
- `CHAT_HANDOFF_BOTA.md`
- `DECISIONS.md`
- `audits/PACKAGE1_CLOCK_AND_PACKAGE2_CONTROL_PLANE_2026-08-09.md`
- `audits/ERROR_LOG.md`
- GitHub issue #9

## Current verdict

```text
DEPLOYED_RELEASE=8728de6b5a2ed0f4647374ef4fa6ed72f9eb03c0
PACKAGE_1_CLOCK_SESSION=PASS
RUNTIME_FILE_PARITY=PASS
ACTIVE_WRAPPER_MODE=755
CURRENT_CONTROL_PLANE=HEALTHY
CURRENT_MANAGER_COUNT=1
CURRENT_MANAGER_PID=4398
CURRENT_OWNED_SERVICES=7/7
CURRENT_RUNNING_SERVICES=7/7
CURRENT_ORPHANED_RUNSV=0
CURRENT_DUPLICATE_SERVICE_ROWS=0
CURRENT_LIVE_CROND_COUNT=1
ACTIVE_WATCHER_CRON=0
ACTIVE_PROFITLAB_CRON=1
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
PROFITLAB_CURSOR=PRESERVED_AT_EOF
PRE_MARKET_PRODUCTION_INTEGRITY=PENDING
OPEN_MARKET_THREE_PAIR_LIVE_PROOF=PENDING
MONDAY_READY=NO
```

Package #1 is fixed and deployed. Package #2 has repaired the live topology but still requires persistent recovery/boot hardening and fault-injected pre-market readiness checks.

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

**Observed during Package #2:** six BotA `runsv` supervisors were alive with PPID 1 while the current manager owned only `crond`.

```text
running=7/7
owned=1/7
orphaned=6
```

**Live fix:** topology reconciled to current native manager PID 4398.

```text
owned=7/7
running=7/7
orphaned=0
duplicate_service_rows=0
```

**Remaining prevention work:** persistent watchdog/boot recovery must automate and test orphan handoff.

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

**Latest proof:** cycle `...:144452448476926` -> `MARKET_CLOSED / MARKET_CLOSED_SUNDAY`, `time_source=server_epoch`.

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

```text
cursor_offset=897734
alerts_csv_size=897734
pending_bytes=0
```

**Prevention:** preserve cursor; do not run `--bootstrap` on current production.

## E015 — Persisted compact-state schema label lag

**Observation:** compact state may retain an older top-level schema label while current events use schema 1.1.

**Classification:** bookkeeping debt unless behavior is affected.

## E016 — Stale event mistaken for current failure

**Observation:** an older shadow failure can remain in compact state after deployment.

**Prevention:** compare timestamp/cycle against deployment and require fresh updater/shadow evidence at the open-market gate.

## E017 — Stale overlapping PRs

**Failure:** old-base PRs can look actionable after architecture moves.

**Containment:** PR #77 closed unmerged; stale draft PR #7 must not be merged wholesale.

## E018 — Calendar before/after exclusion-window sign inversion

**Failure:** `minutes_away = event - now` was paired with reversed before/after comparisons, so configured asymmetric windows were applied in the wrong direction.

**Package #1 fix:** positive `minutes_away` is treated as before-event; negative as after-event. Boundary tests cover HIGH and MEDIUM windows on both sides.

**Prevention:** deterministic signed-boundary tests for every asymmetric event-time window.

## E019 — Nested components established inconsistent cycle time

**Failure:** outer gate could use trusted server time while nested scorer/gates independently re-probed or read another clock.

**Consequence:** one logical watcher cycle could classify market/session/news using different instants.

**Package #1 fix:** inherited `BOTA_SERVER_EPOCH` is reused through the audited strategy/event-time path.

**Prevention:** one immutable event-time reference per production cycle; no silent wall-clock fallback.

## E020 — Stale live singleton daemon blocked manager-owned service

**Failure:** current runit reported `crond` down while an old live PID-1-owned `crond` still executed jobs and held `/var/run/crond.pid`.

Verified incident:

```text
manager_pid=4398
current_runsv_crond_pid=24583
stale_crond_pid=4107
stale_crond_ppid=1
replacement_failure=can't lock crond.pid, otherpid may be 4107
```

This produced a dangerous split-brain-looking state: scheduled business work continued from the stale daemon, but the current control plane could not own the service.

**Live fix:** quiesce failed restart loop -> verify PID/command/parent -> terminate only stale PID 4107 -> let current `runsv` start replacement PID 17994 -> verify PPID 24583 and one stable live `crond`.

**Package #2 remaining fix:** automate safe reconciliation of `manager-owned supervisor + stale live singleton child/resource owner`; distinguish from dead stale pidfile.

## E021 — Health gate checked service liveness without owner lineage

**Failure:** seven services could all report `run` while six `runsv` supervisors were PID-1 orphans.

**Live discovery:** `running=7/7` coexisted with `owned=1/7` and `orphaned=6`.

**Live fix:** supervisors were reconciled to the current manager; final `owned=7/7`, `orphaned=0`.

**Prevention:** production health must require manager count, supervisor lineage, duplicate count, service liveness, and singleton child ownership where applicable.

## E022 — Watchdog code present but persistent recovery disabled

**Failure:** watchdog source files matched GitHub, but no persistent watchdog process was running and phone boot launcher explicitly recorded `RUNSVDIR_GUARD_START=DISABLED`.

**What passed:** a one-shot watchdog execution on the healthy final topology returned RC 0.

**What is still missing:** persistent single-instance startup, manager-loss recovery, and automated stale-live-singleton reconciliation.

**Package #2 status:** PENDING.

## Package #1 fixed-solution summary

```text
DEPLOYED_RELEASE=8728de6b5a2ed0f4647374ef4fa6ed72f9eb03c0
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

## Package #2 required hardening tests

Before persistent phone mutation, isolate and fault-inject:

```text
manager loss
PID-1 orphaned runsv handoff
single service down
dead stale pidfile
live stale singleton child/resource owner
duplicate supervisor
multiple manager attempt
watchdog duplicate attempt
release/blob/config drift
missing/stale updater/shadow/data readiness
```

## Historical strategy-quality evidence remains separate

The June-July replay/outcome evidence remains preserved. Current readiness is an operational proof problem; missing runtime evidence must never be “fixed” by lowering thresholds.

## Current open risks

```text
PACKAGE_2_PERSISTENT_WATCHDOG=OPEN
PACKAGE_2_STALE_SINGLETON_AUTORECOVERY=OPEN
PACKAGE_2_PREMARKET_RELEASE_CONFIG_DATA_GATE=OPEN
ANDROID_WALL_CLOCK_CRON_SCHEDULING=OPEN_WARN
OPEN_MARKET_THREE_PAIR_PROOF=PENDING
SIGNAL_CLOSER_LIFECYCLE=SEPARATE_WORK
H1_ADX_OVERRIDE_CONTRACT=SEPARATE_APPROVAL
COMPACT_STATE_SCHEMA_NORMALIZATION=DEFERRED
```

## Exactly one next engineering action

Complete Package #2 in reviewed code/tests. Do not change the phone again until its fault matrix covers the control-plane failure classes above and the persistent watchdog/boot design preserves exactly one native manager and one supervisor per required service. After Package #2 passes, require the natural open-market three-pair cycle with fresh data/updater/shadow evidence and one authoritative terminal outcome.