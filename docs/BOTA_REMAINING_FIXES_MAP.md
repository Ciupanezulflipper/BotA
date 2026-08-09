# BotA Remaining Fixes Map

Last updated: **2026-08-09 UTC**

This is a current roadmap, not a historical incident log. For immutable evidence, read the dated audits. For current production truth, read `AI_START_HERE.md` and `CONTINUITY_CURRENT.md` first.

## 1) CLOSED — Package #1 Clock & Session Time

Status: **PASS / MERGED / DEPLOYED / LIVE-PROVEN**

Release:

```text
8728de6b5a2ed0f4647374ef4fa6ed72f9eb03c0
```

Resolved failure classes:

- scorer session component using Android wall time;
- nested components deriving inconsistent cycle time;
- economic-calendar timing using wall clock;
- active Finnhub calendar-date selection using wall clock;
- reversed calendar before/after exclusion-window signs.

Production proof:

```text
cycle_id=b32a66a6-1a91-4b61-b759-c32851cbae6b:144452448476926
terminal_outcome=MARKET_CLOSED
market_reason=MARKET_CLOSED_SUNDAY
time_source=server_epoch
server_epoch=1786245830
```

No strategy thresholds or pair scope were changed.

Canonical detail: `audits/PACKAGE1_CLOCK_AND_PACKAGE2_CONTROL_PLANE_2026-08-09.md`.

---

## 2) IN PROGRESS — Package #2 Pre-Market Production Integrity

Status: **LIVE REPAIR PASS / PERSISTENT HARDENING PENDING**

### P2-001 — Stale live singleton child/resource owner

Observed production failure:

```text
current manager PID=4398
current runsv crond PID=24583
stale live crond PID=4107
stale crond PPID=1
stale process held crond.pid
replacement attempts failed every ~1s
```

Live repair: **PASS**.

```text
replacement crond PID=17994
replacement parent runsv=24583
live crond count=1
stability=PASS
```

Still required:

- automate safe detection/reconciliation in reviewed code;
- distinguish a live stale singleton owner from a stale pidfile whose process is dead;
- never blindly remove pidfiles or kill by name.

### P2-002 — PID-1 orphaned `runsv` supervisors

Observed after cron repair:

```text
running=7/7
owned=1/7
orphaned=6
```

Live reconciliation: **PASS**.

Final state:

```text
manager_count=1
manager_pid=4398
owned=7/7
running=7/7
orphaned=0
duplicate_service_rows=0
```

Still required:

- persistent automatic handoff/recovery after manager replacement;
- fault-injected proof rather than manual-only repair.

### P2-003 — Persistent watchdog activation

Current state:

```text
watchdog source parity with GitHub=PASS
one-shot healthy-topology run=PASS
boot launcher RUNSVDIR_GUARD_START=DISABLED
persistent recovery proof=PENDING
```

Required:

- one persistent watchdog instance only;
- start after the native Termux service manager is available;
- no second `runsvdir` manager;
- safe lock/dedup behavior;
- restart/reconcile only the proven failed ownership generation.

### P2-004 — Pre-market immutable release/config/data gate

Required before the natural Monday market-open proof:

```text
approved/deployed runtime SHA and blob parity
active wrapper hash/mode parity
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
Policy B unchanged
active direct watcher cron=0
active ProfitLab cron=1
ProfitLab cursor preserved
one native runsvdir manager
7/7 services owned and running
zero orphaned supervisors
zero duplicate service rows
correct singleton child ownership
trusted clock available
updater/data caches fresh enough for the gate
shadow path current/observable
operational failures surfaced explicitly
```

### Package #2 mandatory fault matrix

Before phone mutation, isolate and test at least:

```text
manager loss
PID-1 orphaned runsv handoff
single service down
dead stale pidfile
live stale singleton child/resource owner
duplicate runsv supervisor
multiple manager attempt
watchdog duplicate attempt
release/blob/config drift
missing or stale updater data
missing or stale shadow evidence
recovery interruption / partial convergence
```

Package #2 must not change trading thresholds or pair selection.

---

## 3) PENDING — Natural open-market three-pair production proof

This runs only after Package #2 passes.

One genuine `MARKET_OPEN` watcher cycle must provide current same-cycle evidence for:

```text
EURUSD:M15 decision
GBPUSD:M15 decision
USDJPY:M15 decision
fresh updater/data evidence
fresh shadow evidence
trusted server epoch
one authoritative watcher terminal outcome
no duplicate watcher owner
7/7 services correctly owned and running
```

Three legitimate rejected/HOLD decisions are acceptable. A Telegram signal is not required.

---

## 4) SEPARATE WORK — Signal closer lifecycle

Status: **PENDING / SEPARATE PACKAGE**

- Draft PR #7 is stale and must not be merged wholesale.
- Re-audit lifecycle semantics against current `main` before salvaging any logic.
- This must not be mixed into Package #2 control-plane hardening.

---

## 5) DEFERRED / SEPARATE APPROVAL

- H1/ADX override contract mismatch.
- Legacy/redundant provider refresh cleanup.
- Android system wall-clock correction and wall-clock cron scheduling behavior.
- Compact state-schema normalization.
- Historical strategy optimization/replay changes.

These are not excuses to modify strategy before the operational gates pass.

## Update rules

1. Move an item to CLOSED only with code/deployment/live proof appropriate to that gate.
2. Keep manual incident repair distinct from persistent automated recovery.
3. Record exact release, topology, and live evidence.
4. Operational failure takes precedence over strategy interpretation.
5. New sessions must start with `AI_START_HERE.md`, not with older April/July snapshots.