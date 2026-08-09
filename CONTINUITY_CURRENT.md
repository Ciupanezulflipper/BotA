# BotA Current Continuity State

Last updated: **2026-08-09 UTC**

This file is the current operational handoff. Dated audit files preserve historical evidence; do not reconstruct current production state from older continuity snapshots.

## Current status

```text
CODE_READY=PASS
MERGED_TO_MAIN=PASS
DEPLOYED_TO_PHONE=PASS
RUNTIME_PARITY_VERIFIED=PASS
PACKAGE_1_CLOCK_SESSION=PASS
CURRENT_CONTROL_PLANE=HEALTHY
CURRENT_REQUIRED_SERVICES_OWNED=7/7
CURRENT_REQUIRED_SERVICES_RUNNING=7/7
CURRENT_ORPHANED_RUNSV=0
CURRENT_DUPLICATE_SERVICE_ROWS=0
CURRENT_LIVE_CROND_COUNT=1
PROFITLAB_STATE=PASS
PRE_MARKET_PRODUCTION_INTEGRITY=PENDING
OPEN_MARKET_THREE_PAIR_LIVE_PROOF=PENDING
MONDAY_READY=NO
```

Package #1 is complete. Package #2 has a repaired live topology but its persistent recovery/boot hardening is not yet complete.

## Authoritative deployed release

```text
DEPLOYED_GITHUB_SHA=8728de6b5a2ed0f4647374ef4fa6ed72f9eb03c0
PHONE_LOCAL_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_LOCAL_HEAD=4339543551aae2e2bcbf727aefe96e3eb103b665
```

The phone worktree is not the deployment identity. Production identity is proven by the immutable release SHA, deployed file blobs/modes, active wrapper parity, runtime configuration, and live watcher evidence.

Active wrapper:

```text
/data/data/com.termux/files/home/.config/bota-sv/bota-watcher/run
blob=25b240dc6913bf9cde82ab79a62ea6cddd73bc8e
mode=755
```

## Deployed production scope

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

No Package #1 threshold or pair-scope changes were made.

## Package #1 — trusted clock/session proof

PR #84 deployed exactly these five runtime files:

```text
tools/calendar_guard.py
tools/market_open.sh
tools/news_filter_real.py
tools/scoring_engine.sh
tools/trusted_time.py
```

Fixed semantics:

- one inherited `BOTA_SERVER_EPOCH` controls market/session/event-time truth within a watcher cycle;
- scorer session component no longer reads Android wall clock;
- economic-calendar distance uses trusted epoch;
- Finnhub date selection uses trusted epoch when active;
- the calendar before/after exclusion-window sign bug is corrected;
- CLOCK_BOOTTIME/monotonic remains the elapsed-time health/cooldown domain.

Pre-deployment gates passed deterministic boundaries, real scorer integration, ShellCheck, Python compile, no-network inherited-clock checks, and a 2,000-case seeded time/timezone fault matrix.

Fresh production proof after deployment:

```text
cycle_id=b32a66a6-1a91-4b61-b759-c32851cbae6b:144452448476926
status=skipped_market_closed
terminal_outcome=MARKET_CLOSED
market_reason=MARKET_CLOSED_SUNDAY
time_source=server_epoch
server_epoch=1786245830
timestamp_utc=2026-08-09T03:23:50+00:00
```

Backup created before Package #1 mutation:

```text
/data/data/com.termux/files/home/BotA-backups/clock-pkg1-20260809T022316Z
```

## Package #2 findings and live repairs

### Stale live `crond` singleton owner

The first Package #1 deployment attempt safely stopped before mutation because `crond` failed the seven-service gate. Forensics proved:

```text
manager_pid=4398
runsv_crond_pid=24583
stale_live_crond_pid=4107
stale_live_crond_ppid=1
pidfile_owner=4107
failure=second crond repeatedly unable to lock crond.pid
```

The stale daemon was identity-checked, the failed restart loop was quiesced, PID 4107 was terminated, and runit started one replacement:

```text
new_crond_pid=17994
new_crond_parent_runsv=24583
live_crond_count=1
crond_stability=PASS
```

### PID-1-orphaned BotA supervisors

Immediately after the cron repair, control-plane inspection exposed six live BotA `runsv` supervisors parented by PID 1 rather than the current native manager. Final topology was reconciled and verified stable:

```text
manager_count=1
manager_pid=4398
owned=7/7
running=7/7
orphaned=0
duplicate_service_rows=0
```

This proves why `running=7/7` alone is insufficient; correct owner lineage is a separate readiness invariant.

### Persistent recovery remains pending

The phone boot launcher currently records:

```text
RUNSVDIR_GUARD_START=DISABLED
```

The watchdog source files match GitHub and a one-shot healthy-topology execution returned RC 0, but the watchdog is not yet proven persistent across boot/runtime manager replacement. The exact stale-live-singleton-child condition seen with `crond` is not yet an automated reviewed recovery case.

Therefore:

```text
LIVE_CONTROL_PLANE_REPAIR=PASS
PACKAGE_2_ENGINEERING_HARDENING=PENDING
```

## ProfitLab state

```text
cursor_offset=897734
alerts_csv_size=897734
pending_bytes=0
```

Do not run `profitlab_delivery.py --bootstrap`.

## Residual observations

- `pipeline_progress.json` can retain a legacy top-level schema label while newer events use schema 1.1; treat as bookkeeping debt unless it affects behavior.
- A stale compact shadow failure record predates the current production state; require fresh shadow evidence at the open-market gate.
- The Android wall clock remains an operational warning, but Package #1 removed its use from the audited market/session/calendar paths. Wall-clock cron scheduling risk must still be treated separately.

## Canonical dated evidence

- `audits/PACKAGE1_CLOCK_AND_PACKAGE2_CONTROL_PLANE_2026-08-09.md`
- `audits/PHONE_DEPLOYMENT_WEEKEND_PROOF_2026-08-09.md`

The first file is current for Package #1/#2 findings. The second remains immutable evidence of the earlier deployment baseline.

## Current freeze

```text
DO_NOT_BOOTSTRAP_PROFITLAB=YES
DO_NOT_LOWER_THRESHOLDS=YES
DO_NOT_FORCE_TELEGRAM_TEST_SIGNAL=YES
DO_NOT_DECLARE_PACKAGE2_COMPLETE_FROM_MANUAL_REPAIR=YES
DO_NOT_DECLARE_MONDAY_READY_FROM_CLOSED_MARKET_PROOF=YES
```

## Exactly one next engineering action

Complete **Package #2 — Pre-Market Production Integrity** in reviewed code/tests before another phone mutation. Fault-inject manager loss, PID-1 orphan handoff, down service, dead stale pidfile, duplicate supervisors, and the exact `current runsv + stale live singleton child/resource owner` condition. Add persistent single-instance watchdog/boot behavior and immutable release/config/data-path readiness checks.

After Package #2 passes, wait for the first genuine `MARKET_OPEN` cycle and prove current EURUSD:M15, GBPUSD:M15, and USDJPY:M15 decisions in the same authoritative cycle with fresh updater/shadow/data evidence, one legitimate terminal outcome, trusted time, and unique ownership. Three legitimate rejected decisions are acceptable; a Telegram signal is not required.