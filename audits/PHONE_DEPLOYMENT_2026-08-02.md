# BotA Phone Deployment State — 2026-08-02

Last updated: 2026-08-02 23:31 UTC

## Purpose

This record reconciles GitHub `main`, the preserved production-phone checkout,
the five-file phone deployment performed on 2026-08-02, and the remaining
runtime gaps. It supersedes earlier statements that the D1 defect was unresolved
or that the phone state was entirely unknown.

## Repository state

Verified GitHub repair baseline:

```text
GITHUB_MAIN=b4d961ea8e5d254c8578e2c022e1394cd134cd7e
```

That baseline contains the focused repository repairs for:

- D1 timeframe mapping and validation;
- cache-only status formatting;
- market-gated autostatus delivery;
- monotonic heartbeat delivery control;
- supervisor clock observability separated from runtime failure.

The production phone was not reset or pulled to that commit. Its existing
phone-only work was preserved first, then five complete repaired files were
applied on a dedicated local branch.

Verified phone state after deployment:

```text
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=d5c765df6fee1241be21ce892fc53e9c4bdcfb8c
PHONE_PARENT_HEAD=66fe241cc6afc8ec4fa21f805b5f52340dac3a32
REMOTE_PUSH_PERFORMED=NO
```

## Preservation evidence

Before any phone reconciliation:

```text
PRESERVE_DIR=~/bota-phone-preserve-20260802T210517Z
WORKTREE_CHANGED_FILES=0
INDEX_CHANGED_FILES=0
UNTRACKED_FILES=519
UNTRACKED_ARCHIVED=YES
LOCAL_CONFIG_FILES_BACKED_UP=8
ACTIVE_CRONTAB_BACKED_UP=YES
ALL_GIT_REFS_BUNDLED=YES
```

The preservation package includes binary Git patches, untracked-file archive,
local configuration copies, crontab snapshot, complete Git bundle, checksums,
and later reconciliation evidence.

## Files deployed to the phone

The following phone files were replaced by complete-file copies verified byte-for-byte
against GitHub baseline `b4d961e`:

```text
tools/supervisor_clock_status.py
tools/build_indicators.py
tools/format_status.py
tools/autostatus.sh
tools/bota_supervisor.sh
```

The deployment was committed locally as:

```text
PHONE_DEPLOYMENT_COMMIT=d5c765df6fee1241be21ce892fc53e9c4bdcfb8c
COMMIT_SUBJECT=deploy: apply repaired non-heartbeat runtime core
```

No service restart, crontab mutation, provider call, Telegram call, Supabase
mutation, strategy change, or remote push was performed by the deployment.

## Verified acceptance results

The targeted phone acceptance package passed:

```text
P6_TARGETED_RUNTIME_ACCEPTANCE=PASS
SUPERVISOR_ACCEPTANCE_SCENARIOS=6
D1_TIMEFRAME_ACCEPTANCE=PASS
FORMATTER_ACCEPTANCE=PASS
AUTOSTATUS_ACCEPTANCE=PASS
PROTECTED_HEARTBEAT_FILES_UNCHANGED=YES
PIPELINE_HEALTH_UNCHANGED=YES
LIVE_TRACKED_MUTATION=NO
LIVE_UNTRACKED_FILES=519
TELEGRAM_CALL_PERFORMED=NO
PROVIDER_CALL_PERFORMED=NO
SERVICE_RESTART_PERFORMED=NO
CRONTAB_MUTATION_PERFORMED=NO
REMOTE_PUSH_PERFORMED=NO
```

The six isolated supervisor scenarios proved:

- market open plus healthy runtime -> `HEALTHY`;
- market closed plus healthy runtime -> `HEALTHY`;
- trusted clock unavailable -> market fail-closed, clock `UNAVAILABLE`, runtime
  not falsely degraded;
- market-gate error -> clock `UNKNOWN`, runtime not falsely degraded;
- control-plane failure -> `DEGRADED`;
- pipeline failure -> `DEGRADED`.

## D1 defect status

The root defect was `tools/build_indicators.py::tf_minutes()` mapping D1 to zero.
The deployed implementation now verifies:

```text
tf_minutes("D1")=1440
tf_minutes("d1")=1440
```

Status:

```text
D1_TIMEFRAME_MAPPING=FIXED_AND_DEPLOYED
D1_LIVE_CACHE_REGENERATION=NOT_YET_RECORDED
```

A later live updater cycle still needs to regenerate and verify the actual D1
cache, but the code-level zero-minute defect is closed.

## Status and autostatus status

Verified deployed behavior:

- formatter reads cache only;
- formatter performs no provider calls;
- output is explicitly technical context, not a trade entry;
- H1, H4, and D1 coverage is validated;
- autostatus does not invoke the formatter or Telegram when the market gate is
  closed or the trusted trading clock is unavailable;
- dry-run rendering exits before Telegram delivery.

## Supervisor status

The active phone runit service reported:

```text
SUPERVISOR_SERVICE_STATUS=run
SUPERVISOR_SERVICE_PID=10711
ACTIVE_WRAPPER_TARGETS_DEPLOYED_SUPERVISOR=YES
```

The deployed `tools/bota_supervisor.sh` is therefore on the active execution
path.

This does not by itself prove all seven service ownership chains. A fresh full
7/7 ownership proof was not part of P6.

## Critical topology inconsistency discovered

The active phone file `services/bota-supervisor/run` is phone-only and is not
tracked on GitHub `main`.

Its loop contains automatic manager mutation:

```text
if no process matches runsvdir.*bota-sv:
    runsvdir -P "$HOME/.config/bota-sv" &
```

That behavior conflicts with the canonical claim that automatic topology
recovery is disabled. It also means the wrapper is not a read-only scheduler for
`tools/bota_supervisor.sh`.

P6 simultaneously recorded:

```text
SUPERVISOR_SERVICE_STATUS=run
RUNSVDIR_PROCESS_SNAPSHOT=none
```

The `none` snapshot may reflect a process-matching defect rather than true
manager absence. Until the exact command and parentage are checked, the wrapper
could repeatedly attempt to start managers.

Status:

```text
AUTOMATIC_TOPOLOGY_RECOVERY=INCONSISTENT_WITH_PHONE_WRAPPER
FULL_CURRENT_OWNERSHIP=UNKNOWN
NEXT_PRIORITY=SUPERVISOR_WRAPPER_TOPOLOGY_RECONCILIATION
```

Do not proceed to heartbeat replacement before this is resolved.

## Heartbeat topology gap

The active phone heartbeat path is:

```text
services/bota-heartbeat/run
  -> tools/bota_heartbeat_utc.sh
```

GitHub `main` instead implements:

```text
tools/heartbeat.sh
  -> tools/heartbeat_delivery.py
```

The GitHub controller provides locking and bounded monotonic retry backoff. The
phone-only UTC wrapper also owns deadman and recovery behavior but may retry a
failed Telegram delivery every 60 seconds. The two implementations are not
interchangeable without preserving deadman semantics.

Status:

```text
HEARTBEAT_ACTIVE_PATH=PHONE_ONLY_UTC_WRAPPER
HEARTBEAT_RETRY_BACKOFF_ON_ACTIVE_PATH=NOT_RECONCILED
HEARTBEAT_DEADMAN_PRESERVATION_REQUIRED=YES
```

Heartbeat reconciliation follows only after the supervisor-wrapper topology is
made non-mutating and verified.

## Files deliberately unchanged

The following were preserved exactly during the five-file deployment:

```text
tools/heartbeat.sh
tools/bota_heartbeat_utc.sh
services/bota-heartbeat/run
tools/pipeline_health.py
```

The active crontab and all 519 untracked runtime/audit files were also preserved.

## Scope lock

No strategy, threshold, scoring, pair, ADX, H1/D1 confirmation, volatility,
macro, deduplication, SL/TP, PR #7, or Supabase signal-semantic changes are
authorized by this record.

## Exact next action

Inspect and replace `services/bota-supervisor/run` with a non-mutating scheduler
that only invokes the deployed supervisor, then verify one intended `runsvdir`,
seven owned/running required services, zero orphans/duplicates, and no automatic
manager creation. Only after that gate passes should heartbeat topology be
reconciled.
