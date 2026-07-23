# Phase 4 Persistent Manager Loss — 2026-07-22

## Status

Phase 4 is reopened. Phase 5 is blocked.

Completed: 3/5.
Remaining: 2/5.

## Confirmed persistent state

A compact control-plane resample on boot
`ae204a40-c3ff-4c4e-abc2-39696b867781` found:

```text
STANDARD_MANAGER_COUNT=0
STANDARD_MANAGER_PID=NONE
CONTROL_PLANE_RESAMPLE=MANAGER_ABSENT
OWNED=0/7
RUNNING=6/7
ORPHANED=6
MISSING_OR_DOWN=crond
```

Current processes:

- updater runsv 24057, PPID 1, wrapper 24070, running;
- watcher runsv 24058, PPID 1, wrapper 24075, running;
- closer runsv 24059, PPID 1, wrapper 24071, running;
- shadow runsv 24060, PPID 1, wrapper 24074, running;
- heartbeat runsv 24065, PPID 1, wrapper 24073, running;
- supervisor runsv 24066, PPID 1, wrapper 24069, running;
- crond runsv absent, stale supervise PID 24068, service down.

## Interpretation

- The manager-loss state persisted across a separate resample.
- This is not a parser or log-routing issue.
- The six surviving services are running only because their orphaned supervisors remain alive under PID 1.
- Crond is unavailable, so cron-based support jobs are unavailable.
- Starting a new manager directly is unsafe because it can create duplicate supervisors beside the six orphans.
- Recovery mutation is justified, but must reuse or derive from the previously validated V5 reconciliation only after verifying its exact hash, approval contract, and rollback artifact.

## Error classification

- E029: standard manager disappeared after 7/7 reconvergence.
- E030: manager absence persisted and crond became definitively unavailable.

## Safety

No runtime mutation, V5 rerun, service restart, rollback, or strategy change has occurred during these diagnostics.

## Next action

Run one compact read-only verification of the existing V5 reconciliation and rollback artifacts. Do not execute them and do not create approval files in the same package.
