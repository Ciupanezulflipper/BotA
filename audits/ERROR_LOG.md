# BotA Runtime Error Log

Last updated: **2026-08-09 UTC**

Canonical compact error/prevention index. Full detail is in `ERRORS.md`, dated audits, and GitHub issue/PR history.

Current sources:

- `audits/PACKAGE1_CLOCK_AND_PACKAGE2_CONTROL_PLANE_2026-08-09.md`
- `CONTINUITY_CURRENT.md`
- `AI_START_HERE.md`
- `CHAT_HANDOFF_BOTA.md`
- `DECISIONS.md`
- `ERRORS.md`
- GitHub issue #9

## Current status

```text
DEPLOYED_RELEASE=8728de6b5a2ed0f4647374ef4fa6ed72f9eb03c0
PACKAGE_1_CLOCK_SESSION=PASS
RUNTIME_PARITY=PASS
CURRENT_CONTROL_PLANE=HEALTHY
MANAGER_COUNT=1
OWNED_SERVICES=7/7
RUNNING_SERVICES=7/7
ORPHANED_RUNSV=0
DUPLICATE_SERVICE_ROWS=0
LIVE_CROND_COUNT=1
ACTIVE_WATCHER_CRON=0
PROFITLAB_CURSOR=PRESERVED_AT_EOF
PRE_MARKET_PRODUCTION_INTEGRITY=PENDING
OPEN_MARKET_THREE_PAIR_PROOF=PENDING
MONDAY_READY=NO
```

## Canonical error index

### E001 — Scope branching
Mixing code/runtime/docs/deployment/strategy phases causes stale truth.

**Prevention:** one bounded package and acceptance gate at a time.

### E002 — Release/worktree identity confusion
Phone HEAD is not deployed runtime identity.

**Prevention:** immutable SHA + deployed blob/mode parity + active-wrapper + config + live proof.

### E003 — Duplicate execution sources
Cron/runit/boot/wrappers can own the same job.

**Prevention:** prove current unique owner; watcher direct cron remains zero.

### E004 — Dead manager with surviving supervisors
`runsv` can survive manager loss and become PID-1 orphans.

**Package #2 observed:** `running=7/7`, `owned=1/7`, `orphaned=6`.

**Live repair:** final `owned=7/7`, `orphaned=0` under manager PID 4398.

### E005 — Clock-domain mixing
Android wall clock leaked into strategy/event semantics.

**Package #1 fix:** one inherited trusted server epoch for market/session/calendar/news semantics; CLOCK_BOOTTIME/monotonic retained for elapsed-time health/cooldowns.

### E006 — Partial pair observability
Health can pass while a production pair disappears.

**Fix:** three-pair EURUSD/GBPUSD/USDJPY M15 observability; final open-market proof still pending.

### E007 — Pre-journal dedup
Delivery/dedup previously interfered with complete decision evidence.

**Prevention:** persist decision evidence independently from delivery.

### E008 — Inner watcher failure hidden by aggregates
Semantic evidence must not hide current execution failure.

**Fix:** operational failure dominates aggregate outcome.

### E009 — Missing watcher terminal outcome
Liveness is not enough.

**Fix:** coherent cycle ID + append-only ledger + authoritative terminal outcome.

### E010 — Moving `main` during deployment

**Fix:** immutable SHA + final remote-pin recheck before mutation.

### E011 — Non-executable runit wrapper
Mode `100644` prevented watcher activation.

**Fix:** PR #81 -> `100755`; verify modes as release parity.

### E012 — Wrong service-root assumption

**Fix:** canonical `$PREFIX/var/service`; resolve external watcher wrapper separately.

### E013 — Deployment manifest drift

**Prevention:** exact parity-audited manifest and expected file count.

### E014 — ProfitLab cursor replay risk

**Current:** offset/size `897734`, pending `0`.

**Prevention:** preserve cursor; no `--bootstrap`.

### E015 — Compact state schema lag
Bookkeeping label can lag current event schema.

**Classification:** deferred unless behaviorally material.

### E016 — Stale event mistaken for current failure
Old shadow/component events must be timestamped against deployment/current cycle.

### E017 — Stale overlapping PR
PR #77 closed as superseded; stale PR #7 must not be merged wholesale.

### E018 — Calendar before/after sign inversion
Asymmetric event windows were applied in the wrong direction.

**Package #1 fix:** signed boundary logic corrected and tested.

### E019 — Inconsistent nested cycle time
Nested components could derive another `now` than the outer gate.

**Package #1 fix:** reuse inherited `BOTA_SERVER_EPOCH` through audited strategy/event path.

### E020 — Stale live singleton child blocked current supervisor
Old live `crond` PID 4107, PPID 1, held `crond.pid` while current `runsv crond` PID 24583 retried replacements every ~1s.

**Live fix:** identity-check -> quiesce -> terminate stale daemon -> current runsv starts PID 17994 -> verify parent/stability/one live crond.

**Remaining Package #2 fix:** automate this safely and distinguish it from a dead stale pidfile.

### E021 — Running service without correct owner lineage
Seven `sv status=run` rows coexisted with six PID-1-orphan supervisors.

**Prevention:** health requires manager count + supervisor lineage + duplicates + service liveness + singleton-child ownership.

### E022 — Watchdog source present but persistent recovery disabled
Phone boot launcher records `RUNSVDIR_GUARD_START=DISABLED`.

**Current proof:** source matches GitHub; one-shot healthy-topology watchdog run RC 0.

**Missing:** persistent single-instance boot/runtime recovery and stale-live-singleton automation.

## Package #1 live acceptance proof

```text
release=8728de6b5a2ed0f4647374ef4fa6ed72f9eb03c0
cycle_id=b32a66a6-1a91-4b61-b759-c32851cbae6b:144452448476926
terminal_outcome=MARKET_CLOSED
market_reason=MARKET_CLOSED_SUNDAY
time_source=server_epoch
server_epoch=1786245830
runtime_parity=PASS
rollback=NO
```

## Package #2 required fault matrix

```text
manager loss
PID-1 orphaned runsv handoff
service down
dead stale pidfile
live stale singleton child/resource owner
duplicate supervisor
multiple manager attempt
watchdog duplicate attempt
release/blob/config drift
missing/stale updater/shadow/data readiness
```

## Current unresolved risks

```text
PACKAGE_2_PERSISTENT_WATCHDOG=PENDING
PACKAGE_2_STALE_SINGLETON_AUTORECOVERY=PENDING
PACKAGE_2_PREMARKET_RELEASE_CONFIG_DATA_GATE=PENDING
ANDROID_WALL_CLOCK_CRON_SCHEDULING=OPEN_WARN
OPEN_MARKET_THREE_PAIR_PROOF=PENDING
SIGNAL_CLOSER_LIFECYCLE=SEPARATE_WORK
H1_ADX_OVERRIDE_CONTRACT=SEPARATE_APPROVAL
COMPACT_STATE_SCHEMA_NORMALIZATION=DEFERRED
```

## Exactly one next action

Complete Package #2 in reviewed code/tests before another phone mutation. Then, after Package #2 passes, require one natural `MARKET_OPEN` cycle proving EURUSD:M15, GBPUSD:M15, USDJPY:M15, fresh updater/shadow/data evidence, trusted time, unique ownership, 7/7 correct manager ownership, and one authoritative watcher terminal outcome. Three legitimate rejects are acceptable.