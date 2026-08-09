# BotA Package #1 / Package #2 Production Findings — 2026-08-09

Status: **authoritative dated audit**

This record preserves the verified production facts from the trusted-clock deployment and the control-plane incident discovered while deploying it. It supersedes older *current-status* summaries where they conflict, but it does not rewrite historical evidence in earlier dated audits.

## Executive status

```text
PACKAGE_1_CLOCK_SESSION=PASS
PACKAGE_1_MERGED=PASS
PACKAGE_1_DEPLOYED=PASS
PACKAGE_1_RUNTIME_PARITY=PASS
PACKAGE_1_LIVE_PROOF=PASS
PACKAGE_2_LIVE_CONTROL_PLANE_REPAIR=PASS
PACKAGE_2_PERSISTENT_HARDENING=PENDING
OPEN_MARKET_THREE_PAIR_PROOF=PENDING
MONDAY_READY=NO
```

## Package #1 — Clock & Session Time

### Problem

Post-deployment audit had shown the Android wall clock about one hour behind trusted server UTC. The outer watcher market gate was already server-clock based, but nested strategy/event-time consumers could still use or independently derive another `now`.

Verified unsafe/ambiguous consumers before the fix:

1. `tools/scoring_engine.sh` session score could derive from Android wall time and therefore shift score at session boundaries.
2. Nested `market_open.sh` calls could re-probe time instead of reusing the parent watcher cycle epoch.
3. `tools/calendar_guard.py` used wall-clock time for economic-event distance.
4. `tools/news_filter_real.py` used wall-clock time when selecting the Finnhub calendar date.
5. Calendar audit also found a pre-existing sign error: configured before/after exclusion windows were applied in the wrong direction.

### Design decision

One production watcher cycle owns one trusted strategy/event instant:

```text
watcher_gated_cycle
  -> BOTA_SERVER_EPOCH
     -> market gate
     -> scorer/session component
     -> economic calendar guard
     -> news-calendar date
```

`CLOCK_BOOTTIME`/monotonic remains the correct domain for elapsed-duration health, cadence, and same-boot cooldown logic. Android wall clock is not trading truth.

### GitHub implementation

PR #84: `fix: bind strategy session semantics to trusted UTC`

Merged/deployed release:

```text
8728de6b5a2ed0f4647374ef4fa6ed72f9eb03c0
```

Production runtime delta deployed from that release:

```text
tools/calendar_guard.py    blob=8b16db8948dfc1006574f9389e5e6e9888116f6e mode=100644
tools/market_open.sh       blob=e91cf248f8e87fa14b4b2af1da9b03441642ed38 mode=100755
tools/news_filter_real.py  blob=25b523d2b9a7f10469a7f7f095a3c4dfbe9746f7 mode=100644
tools/scoring_engine.sh    blob=4d1d7c9c6096d2a95bd9688df429b75391664785 mode=100755
tools/trusted_time.py      blob=2a89e640788812d36eb900a6d4e938c28f867cc8 mode=100644
```

Active watcher wrapper remained unchanged and verified:

```text
path=/data/data/com.termux/files/home/.config/bota-sv/bota-watcher/run
blob=25b240dc6913bf9cde82ab79a62ea6cddd73bc8e
mode=755
```

### Pre-deployment validation

The package passed:

```text
bash -n=PASS
ShellCheck Bash gate=PASS
Python compile=PASS
trusted-time deterministic boundaries=PASS
calendar before/after boundaries=PASS
no-network inherited-epoch market boundaries=PASS
real scorer session-boundary integration=PASS
2,000-case seeded randomized time/timezone fault matrix=PASS
```

Real scorer simulation preserved the existing score values while proving the clock source change:

```text
11:59 UTC -> session_london  -> score=75.1
12:00 UTC -> session_overlap -> score=78.1
expected session-only delta=3.0
```

No score threshold or session-score value was changed.

### Production deployment proof

Backup:

```text
/data/data/com.termux/files/home/BotA-backups/clock-pkg1-20260809T022316Z
```

All five runtime files passed byte-for-byte parity against release `8728de6...`. `.env.runtime` remained:

```text
PAIRS="EURUSD GBPUSD USDJPY"
TIMEFRAMES="M15"
```

Only `bota-watcher` was restarted for the package.

Fresh production terminal event after restart:

```text
cycle_id=b32a66a6-1a91-4b61-b759-c32851cbae6b:144452448476926
status=skipped_market_closed
terminal_outcome=MARKET_CLOSED
market_reason=MARKET_CLOSED_SUNDAY
time_source=server_epoch
server_epoch=1786245830
timestamp_utc=2026-08-09T03:23:50+00:00
```

This is the live Package #1 acceptance proof.

Post-deployment invariants:

```text
CLOCK_PACKAGE_CONTENT_PARITY=PASS
TRUSTED_TIME_HELPER=DEPLOYED
MARKET_GATE_TRUSTED_EPOCH=DEPLOYED
SESSION_SCORE_TRUSTED_EPOCH=DEPLOYED
CALENDAR_WINDOW_FIX=DEPLOYED
NEWS_DATE_TRUSTED_EPOCH=DEPLOYED
THRESHOLDS_CHANGED=NO
PAIR_SCOPE_CHANGED=NO
ACTIVE_WATCHER_CRON=0
PROFITLAB_CURSOR_OFFSET=897734
PROFITLAB_ALERTS_SIZE=897734
PROFITLAB_PENDING_BYTES=0
RUNTIME_PROOF=PASS
ROLLED_BACK=NO
```

## Package #2 — Pre-Market Production Integrity findings

Package #2 is not yet fully implemented. However, Package #1 deployment exposed and allowed us to repair two concrete production control-plane failures. Those findings are now mandatory Package #2 test cases.

### Finding P2-E01 — stale live singleton daemon blocked manager-owned replacement

The first Package #1 deployment attempt aborted before mutation because the seven-service gate saw `crond` down.

Forensics proved:

```text
crond service run file = exec crond -n -s
crond binary = installed / executable
cronie version = 1.7.2-4
manager PID = 4398
manager PATH = $PREFIX/bin
runsv crond PID = 24583, parent=4398
pidfile = $PREFIX/var/run/crond.pid
pidfile owner PID = 4107
PID 4107 command = crond -n -s
PID 4107 parent = 1
```

The live orphan daemon PID 4107 still held the singleton pidfile while the current manager-owned `runsv crond` tried to start another daemon every second. Each replacement exited with:

```text
(CRON) DEATH (can't lock .../crond.pid, otherpid may be 4107): Try again
```

Cron jobs were still being executed by the stale live daemon, so business activity existed while control-plane ownership was incorrect. This is exactly why `service_running` and `owner_correct` must remain separate health dimensions.

### Live repair of P2-E01

The repair was bounded and identity-checked:

1. prove exactly one current `runsv crond`;
2. prove pidfile owner was live `crond -n -s` and not a child of current `runsv`;
3. quiesce the current failed restart loop;
4. terminate only the verified stale daemon PID 4107;
5. allow runit to start a replacement;
6. prove the new daemon is the child of current `runsv`;
7. require one stable live `crond`.

Result:

```text
OLD_CROND_PID=4107
NEW_CROND_PID=17994
NEW_CROND_PARENT_RUNSV=24583
LIVE_CROND_COUNT=1
CROND_STABILITY=PASS
CROND_SINGLE_OWNER_REPAIR=PASS
```

No crontab, strategy, BotA runtime file, watcher, ProfitLab state, or boot file was changed by this repair.

### Finding P2-E02 — six surviving `runsv` supervisors were PID-1 orphans

Immediately after the crond repair, `control_plane_status.py` exposed a second topology defect:

```text
manager_count=1
manager_pid=4398
running=7/7
owned=1/7
orphaned=6
```

Six BotA supervisors were alive but parented by PID 1 rather than the current native Termux `runsvdir`. Service liveness alone would therefore have produced a false healthy interpretation.

Affected services were:

```text
bota-updater
bota-watcher
bota-closer
bota-shadow
bota-heartbeat
bota-supervisor
```

The current topology was subsequently reconciled back to the native manager and proven stable:

```text
manager_count=1
manager_pid=4398
owned=7/7
running=7/7
orphaned=0
duplicate_service_rows=0
crond_owner=manager
live_crond_count=1
```

A one-shot run of the current native service-daemon watchdog returned RC 0 against the healthy final topology.

### Finding P2-E03 — watchdog persistence is disabled

The phone's current boot launcher explicitly records:

```text
RUNSVDIR_GUARD_START=DISABLED
```

Before the one-shot validation, no persistent `native_service_daemon_watchdog.py` process was running. The watchdog source files themselves matched GitHub exactly, so this is an activation/persistence gap rather than source drift.

Therefore the present control plane is healthy **now**, but automatic post-manager-loss recovery is not yet proven persistent across boot/runtime manager replacement.

### Required Package #2 engineering work

Package #2 must not be marked complete until reviewed code/tests and live proof cover at least:

1. persistent single-instance native watchdog startup after Termux boot/service-manager activation;
2. PID-1 orphaned `runsv` handoff to the current manager;
3. down-service recovery;
4. stale pidfile with dead process;
5. **live stale singleton child/resource owner** while the current manager-owned `runsv` is trying to restart the service — the exact `crond` incident;
6. duplicate supervisor detection;
7. one native `runsvdir` manager only;
8. seven required services owned and running;
9. immutable deployed-release/runtime blob and active-wrapper identity;
10. production config provenance (`EURUSD GBPUSD USDJPY`, `M15`, Policy B unchanged);
11. active watcher cron count zero;
12. ProfitLab cron count one and cursor preserved;
13. fresh updater/data/shadow readiness before the open-market gate;
14. no strategy mutation as a response to operational failure.

The implementation should be fault-injected in isolation before any new phone mutation. Package #2 must distinguish **recovery action** from **business/service state** and must not create another competing manager or supervisor generation.

## Current production classification after these events

```text
DEPLOYED_RELEASE=8728de6b5a2ed0f4647374ef4fa6ed72f9eb03c0
CLOCK_SESSION_PACKAGE=PASS
CURRENT_CONTROL_PLANE=HEALTHY
CURRENT_MANAGER_PID=4398
CURRENT_REQUIRED_SERVICES_OWNED=7/7
CURRENT_REQUIRED_SERVICES_RUNNING=7/7
CURRENT_ORPHANED_RUNSV=0
CURRENT_DUPLICATE_SERVICE_ROWS=0
CURRENT_LIVE_CROND_COUNT=1
PERSISTENT_WATCHDOG_HARDENING=PENDING
PRE_MARKET_PRODUCTION_INTEGRITY=PENDING
OPEN_MARKET_THREE_PAIR_PROOF=PENDING
MONDAY_READY=NO
```

## Operating rule going forward

Do not confuse the successful live repair with completion of Package #2. The current state is healthy, but the failure must be made reproducibly recoverable in reviewed code and boot/runtime supervision before Package #2 can close.

After Package #2 passes, the final readiness gate remains one natural `MARKET_OPEN` cycle proving current EURUSD:M15, GBPUSD:M15, and USDJPY:M15 decisions in the same watcher cycle with fresh updater/shadow/data evidence, one authoritative terminal outcome, trusted time, and unique ownership. Three legitimate rejected decisions remain acceptable; no forced Telegram signal is required.
