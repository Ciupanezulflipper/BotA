# BotA Chat Handoff

Last updated: **2026-08-09 UTC**

Read this first in any new AI session before proposing BotA changes.

## Current grounded answer

```text
DEPLOYED_RELEASE=8728de6b5a2ed0f4647374ef4fa6ed72f9eb03c0
PACKAGE_1_CLOCK_SESSION=PASS
CURRENT_CONTROL_PLANE=HEALTHY
CURRENT_REQUIRED_SERVICES_OWNED=7/7
CURRENT_REQUIRED_SERVICES_RUNNING=7/7
CURRENT_ORPHANED_RUNSV=0
CURRENT_DUPLICATE_SERVICE_ROWS=0
CURRENT_LIVE_CROND_COUNT=1
PRE_MARKET_PRODUCTION_INTEGRITY=PENDING
OPEN_MARKET_THREE_PAIR_PROOF=PENDING
MONDAY_READY=NO
```

Package #1 is complete and live-proven. Package #2 has already produced important live findings and repairs, but its persistent recovery/pre-market hardening is not complete.

## Production release identity

```text
APPROVED_AND_DEPLOYED_SHA=8728de6b5a2ed0f4647374ef4fa6ed72f9eb03c0
PHONE_LOCAL_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_LOCAL_HEAD=4339543551aae2e2bcbf727aefe96e3eb103b665
```

The phone worktree HEAD is not production identity. Use immutable approved SHA + deployed blob/mode parity + active wrapper + runtime configuration + live evidence.

Active physical watcher wrapper:

```text
/data/data/com.termux/files/home/.config/bota-sv/bota-watcher/run
blob=25b240dc6913bf9cde82ab79a62ea6cddd73bc8e
mode=755
```

## Runtime configuration

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

Do not loosen strategy thresholds to manufacture signals.

## Package #1 — completed trusted-time package

PR #84 deployed exactly five runtime files:

```text
tools/calendar_guard.py
tools/market_open.sh
tools/news_filter_real.py
tools/scoring_engine.sh
tools/trusted_time.py
```

It fixed:

- scorer session time reading unsafe Android wall clock;
- nested market-gate time reprobes instead of inherited cycle epoch;
- calendar event-window calculations using wall clock;
- Finnhub calendar-date selection using wall clock when active;
- reversed before/after economic-calendar block semantics.

One watcher cycle now reuses one `BOTA_SERVER_EPOCH` for strategy/event-time semantics. CLOCK_BOOTTIME/monotonic remains for elapsed-duration health/cooldowns.

Validation passed deterministic boundaries, real scorer integration, ShellCheck, Python compile, no-network inherited-clock checks, and a 2,000-case seeded time/timezone fault matrix.

Fresh live Package #1 evidence:

```text
cycle_id=b32a66a6-1a91-4b61-b759-c32851cbae6b:144452448476926
terminal_outcome=MARKET_CLOSED
market_reason=MARKET_CLOSED_SUNDAY
time_source=server_epoch
server_epoch=1786245830
timestamp_utc=2026-08-09T03:23:50+00:00
```

## Package #2 — findings already discovered

### 1. Stale live `crond` blocked the manager-owned replacement

The first Package #1 deployment attempt aborted before mutation because `crond` looked down. Root cause:

```text
native manager PID=4398
current runsv crond PID=24583
stale crond PID=4107
stale crond PPID=1
stale crond still held crond.pid
new crond attempts failed every ~1 second on pidfile lock
```

The old process was still executing cron jobs, so apparent business activity did not mean correct control-plane ownership.

Repair result:

```text
old crond PID=4107 terminated after identity/parent verification
new crond PID=17994
new crond PPID=24583
live crond count=1
stability=PASS
```

### 2. Six `runsv` supervisors were PID-1 orphans

Immediately after the cron repair, `control_plane_status.py` found:

```text
running=7/7
owned=1/7
orphaned=6
```

Final reconciled topology:

```text
manager_count=1
manager_pid=4398
running=7/7
owned=7/7
orphaned=0
duplicate_service_rows=0
```

Never treat `sv status=run` or process presence alone as proof of correct control-plane ownership.

### 3. Persistent watchdog is still disabled

Phone boot launcher currently records:

```text
RUNSVDIR_GUARD_START=DISABLED
```

The watchdog files match GitHub and a one-shot healthy-topology run passed, but persistent startup/recovery is not proven. Package #2 must automate and fault-test the exact stale-live-singleton-child condition rather than relying on manual repair.

## ProfitLab

```text
cursor_offset=897734
alerts_csv_size=897734
pending_bytes=0
```

Do not run `profitlab_delivery.py --bootstrap`.

## What Package #2 must prove

Before persistent phone changes, fault-inject in isolation:

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
missing/stale updater or shadow evidence
```

The final design must preserve one native `runsvdir`, one supervisor per service, one live singleton child where applicable, one watcher owner, and immutable release/config provenance.

## Canonical evidence

Read:

1. `audits/PACKAGE1_CLOCK_AND_PACKAGE2_CONTROL_PLANE_2026-08-09.md`
2. `CONTINUITY_CURRENT.md`
3. `DECISIONS.md`
4. `ERRORS.md`
5. GitHub issue #9

Older dated audits remain historical evidence and should not be rewritten to look current.

## Final readiness gate after Package #2

The first genuine `MARKET_OPEN` production cycle must prove in one current cycle:

```text
EURUSD:M15 decision present
GBPUSD:M15 decision present
USDJPY:M15 decision present
fresh updater/data evidence
fresh shadow evidence
one authoritative watcher terminal outcome
trusted server time
no duplicate watcher owner
7/7 services correctly owned and running
```

Three legitimate rejected decisions are acceptable. A Telegram signal is not required.

## Exactly one next action

Finish **Package #2 — Pre-Market Production Integrity** in reviewed code/tests before changing the phone again. Do not merge stale signal-closer PR #7 into this package and do not change strategy thresholds to compensate for operational failures.