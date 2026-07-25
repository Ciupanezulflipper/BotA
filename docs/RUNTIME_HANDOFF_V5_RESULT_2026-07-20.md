# BotA V5 Control-Plane Handoff Result — 2026-07-20

## Result

The approved V5 seven-service reconciliation completed successfully on boot:

`ae204a40-c3ff-4c4e-abc2-39696b867781`

Final result markers:

- `V5_EXIT_CODE=0`;
- `V5_INDEPENDENT_POST_VERIFY=PASS`;
- `V5_POST_VERIFY_EXIT_CODE=0`;
- `PHASE4_CONTROL_PLANE_HANDOFF=PASS`;
- `RUNTIME_CHANGE=SUPERVISOR_OWNERSHIP_ONLY`;
- `CODE_OR_STRATEGY_CHANGED=NO`;
- `CRONTAB_CHANGED=NO`;
- `RAPIDAPI_RUNTIME_DISABLE_PRESERVED=YES`.

Phase 4 remains open only for bounded endurance evidence. Phase count remains 3/5 complete, 2/5 remaining.

## Approved artifacts

Stage directory:

`audits/p4_control_plane_reconcile_1bd27eb5_49498`

- V5 executor: `RECONCILE_BOTA_RUNSV_V5_FILE_APPROVAL.py`
  - SHA-256: `ac67fa2b53f1d9a3034e417f5ddf940fc17cf9a09817354211d88aa9468c6e46`;
  - mode: `700`.
- Availability rollback: `ROLLBACK_RECONCILE_BOTA_RUNSV_V5.sh`
  - SHA-256: `518f8f8d2bbed4791a41821e87ea8576828a03ab43d97982c63753573566132c`;
  - mode: `700`.

Both exact current-boot approval files passed audit and were consumed before mutation.

## Preflight

Verified immediately before execution:

- one standard `runsvdir` manager, PID `4090`, PPID 1;
- all seven service supervisors were orphaned under PID 1;
- all seven services were running;
- one live crond;
- V5 and rollback hashes matched;
- approval contents and modes matched;
- boot approval matched the current boot;
- `RAPIDAPI_CALENDAR_KEY` remained declared exactly once and empty in `.env.runtime`.

Preflight result:

`V5_EXECUTION_PREFLIGHT=PASS`

## Handoff behavior

For each of the seven services, V5:

1. revalidated the same standard manager;
2. confirmed the service's current owner chain;
3. waited for the required idle boundary;
4. created a temporary `down` marker;
5. stopped the old wrapper;
6. exited the old orphaned `runsv`;
7. waited for the standard manager to acquire the service;
8. removed all temporary `down` markers;
9. brought every service back up;
10. performed final ownership and status verification.

Services transferred:

- `bota-updater`;
- `bota-watcher`;
- `bota-closer`;
- `bota-shadow`;
- `bota-heartbeat`;
- `bota-supervisor`;
- `crond`.

No recovery rollback was required.

## Final ownership

Standard manager:

- PID `4090`.

Manager-owned supervisors:

- updater runsv PID `26864`;
- watcher runsv PID `26917`;
- closer runsv PID `26978`;
- shadow runsv PID `27166`;
- heartbeat runsv PID `27195`;
- supervisor runsv PID `27217`;
- crond runsv PID `27331`.

Running wrappers immediately after handoff:

- updater PID `27338`;
- watcher PID `27405`;
- closer PID `27410`;
- shadow PID `27430`;
- heartbeat PID `27438`;
- supervisor PID `27463`;
- crond PID `27569`.

Exactly one live `crond -n -s` was present and its PPID was the manager-owned crond `runsv` PID `27331`.

## Independent verification

Three consecutive post-handoff samples all passed:

- one standard manager in every sample;
- manager PID remained `4090`;
- all seven `runsv` PIDs remained unchanged;
- every service remained manager-owned and running;
- one supervised crond remained present;
- boot ID remained unchanged;
- RapidAPI runtime disable remained active.

Stability markers:

- `POST_MANAGER_PID_STABLE=YES`;
- `POST_RUNSV_PID_SET_STABLE=YES`;
- `V5_INDEPENDENT_POST_VERIFY=PASS`.

## Safety conclusion

Do not rerun V5 or its rollback while the current control plane remains healthy.

The remaining Phase 4 task is bounded endurance verification of the same manager PID, supervisor ownership, service progress, one supervised crond, stable resource use, and absence of unexplained outage or duplicate execution.

Deferred work remains separate:

- root cause of prior standard-manager death;
- permanent calendar invocation/caching fix;
- canonical crontab verification mismatch;
- health-truth and stale-reason suppression fixes;
- Twelve Data call budgeting;
- external independent dead-man monitoring.
