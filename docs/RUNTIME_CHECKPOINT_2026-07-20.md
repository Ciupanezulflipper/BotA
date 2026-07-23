# BotA Runtime Checkpoint — 2026-07-20

## Purpose

This document records the verified runtime-control-plane, API-quota, crontab, and observability findings discovered during Phase 4 stabilization. It is the detailed evidence source for `CONTINUITY_CURRENT.md`, `AI_START_HERE.md`, and GitHub issue #9.

## Phase status

- Phase 1 — single execution source and cron hygiene: COMPLETE.
- Phase 2 — runtime survival controls: COMPLETE.
- Phase 3 — ship-time safety proof: COMPLETE.
- Phase 4 — reboot and endurance proof: IN PROGRESS.
  - reboot gate: PASS and closed;
  - endurance/control-plane ownership: FAIL and unresolved.
- Phase 5 — Monday readiness/data collection: NOT STARTED.
- Completed: 3/5.
- Remaining: 2/5.

## Scope lock

Do not change during this reliability incident:

- strategy;
- thresholds;
- pairs;
- scoring;
- SL/TP;
- filters;
- PR #7;
- DeepSource work;
- Supabase signal semantics;
- direct pushes to `main`;
- unrelated cleanup or broad refactors.

## Device and runtime facts

- Runtime: Android 16 / Termux 0.118.3.
- Repository checkout: `/data/data/com.termux/files/home/BotA`.
- Shortcut: `~/BotA`.
- Current verified boot ID: `ae204a40-c3ff-4c4e-abc2-39696b867781`.
- Canonical service root: `$PREFIX/var/service`.
- Correct foreground crond form: `crond -n -s`.
- Ship-time wall clock is not authoritative for trading or freshness decisions.

## Control-plane findings

### Initial new-boot snapshot

The fresh boot audit showed:

- one standard manager:
  - PID 25793;
  - PPID 1;
  - command: `runsvdir $PREFIX/var/service`;
- six BotA `runsv` supervisors orphaned under PID 1:
  - `bota-updater`;
  - `bota-watcher`;
  - `bota-closer`;
  - `bota-shadow`;
  - `bota-heartbeat`;
  - `bota-supervisor`;
- one manager-owned `runsv crond`;
- empty `crond/supervise/pid`;
- one old live orphaned `crond -n -s` under PID 1;
- stable runsv PID sets across three samples.

This proved a split-brain layout rather than a transient PID-file race.

### File-gated crond repair

The V2 file-gated repair was staged at:

`audits/p4_control_plane_reconcile_1bd27eb5_49498/RECONCILE_CROND_SPLIT_BRAIN_V2_FILE_APPROVAL.py`

Pinned repair SHA-256:

`15339b92901508b267e26a31638c237fb481f551af87c6bc0a8acb3440a80876`

Persistent log evidence proves the repair executed:

- `APPROVAL_RESULT=ACCEPTED`;
- accepted challenge: `7C4E91`;
- preflight manager PID 25793;
- manager-owned runsv crond PID 29960;
- old orphaned crond PID 29386;
- idle-boundary proof passed;
- `sv -w 5 down crond` passed;
- SIGTERM sent to PID 29386;
- old crond exited;
- first `sv -w 30 up crond` timed out with rc 111;
- automatic availability recovery started;
- recovery `sv -w 15 up crond` passed;
- supervised crond PID 28296 came up;
- recovery rollback finished successfully.

Conclusion:

- the old detached crond was removed;
- one supervised crond was restored;
- the crond split-brain repair must not be rerun;
- the crond rollback must not be run unless a new verified failure explicitly requires it.

### Latest control-plane snapshot

The latest compact read-only snapshot showed:

- `STANDARD_MANAGER_COUNT=1`;
- standard manager PID `4090`, PPID 1;
- all six BotA `runsv` supervisors remain orphaned under PID 1;
- `runsv crond` also remains orphaned under PID 1;
- all seven services report `run`;
- one live supervised crond PID `28296`, PPID `29960`;
- no runtime mutation occurred during the snapshot.

The manager has therefore reappeared, but it owns none of the seven services because the orphaned `runsv` processes retain the supervise locks.

Current structural blocker:

Migrate all seven stable orphaned supervisors beneath the existing standard manager without duplicate wrappers, historical replay, or service-state corruption.

### V5 file-gated seven-service reconciliation — STAGED AND VALIDATED

The pinned V4 base was inspected completely before reuse:

- V4 SHA-256: `0ca9276096f2e97af13365feefbc397e59b8cc9fe5e21fe0750abd99620d0e19`;
- original rollback SHA-256: `09f7be4ec893649cdd6b1fa5256b33f285802d4aae069f463817dd47d039372f`;
- V4 syntax: PASS;
- no hard-coded boot UUIDs or observed PIDs;
- handoff sequence includes manager revalidation, idle boundaries, temporary `down` markers, wrapper shutdown, orphan `runsv` exit, standard-manager acquisition, final `up`, final verification, and automatic availability rollback;
- V4 must not be executed because it still uses `secrets.token_hex()` and blocking `input()` approval.

V5 was deterministically transformed from the pinned V4 and replaces only the approval boundary with exact, mode-600, single-use, current-boot-bound approval files.

Staged artifacts:

- `audits/p4_control_plane_reconcile_1bd27eb5_49498/RECONCILE_BOTA_RUNSV_V5_FILE_APPROVAL.py`;
  - SHA-256: `ac67fa2b53f1d9a3034e417f5ddf940fc17cf9a09817354211d88aa9468c6e46`;
  - mode: `700`;
- `audits/p4_control_plane_reconcile_1bd27eb5_49498/ROLLBACK_RECONCILE_BOTA_RUNSV_V5.sh`;
  - SHA-256: `518f8f8d2bbed4791a41821e87ea8576828a03ab43d97982c63753573566132c`;
  - mode: `700`.

Semantic validation evidence:

- V5 present: YES;
- rollback present: YES;
- Python syntax: PASS;
- rollback shell syntax: PASS;
- exact seven-service set: PASS;
- `run_sv` call count: 5;
- `wait_for_idle_boundary` call count: 1;
- `wait_manager_acquisition` call count: 1;
- `final_verify` call count: 1;
- `recovery_rollback` call count: 1;
- required file-gated approval and pass tokens: PASS;
- prohibited interactive/secrets tokens: NONE;
- hard-coded UUID count: 0;
- semantic validation: PASS;
- V5 executed: NO;
- approval files created: NO;
- runtime mutation performed: NO.

Required approval files before execution:

- `APPROVE_P4_CONTROL_PLANE_V5.txt` containing exactly `APPROVE P4 CONTROL PLANE RECONCILIATION V5 4A73C2`;
- `APPROVED_BOOT_ID_P4_CONTROL_PLANE_V5.txt` containing the current boot ID;
- both files mode `600`.

Do not execute V5 without fresh approval-file verification and a current boot-ID match.

## RapidAPI calendar quota incident

### External warning

The Global Economic Calendar API BASIC subscription reached 100% usage. This creates a real overage or blocking risk depending on the provider's plan behavior.

This is separate from Twelve Data usage. Telegram reported Twelve Data at 600/800 credits.

### Proven active caller

The active caller chain is:

```text
bota-watcher runit service
  -> tools/signal_watcher_pro.sh --once every 900 seconds
  -> tools/calendar_guard.py once per pair path
  -> TradingEconomics guest source
  -> RapidAPI fallback when TradingEconomics returns no events
```

The watcher source contains a misleading comment saying the calendar guard is disabled, but the condition is logically always true whenever `calendar_guard.py` exists:

```bash
if [[ -f "${TOOLS}/calendar_guard.py" && -n "${RAPIDAPI_CALENDAR_KEY:-}" ]] || [[ -f "${TOOLS}/calendar_guard.py" ]]; then
```

Therefore the second clause bypasses the intended key/enable gate.

Additional proof:

- `.env` contains one non-empty `RAPIDAPI_CALENDAR_KEY` declaration;
- `.env.runtime` originally contained one non-empty declaration;
- recent `cron.signals.log` lines showed:
  - `CLEAR: EURUSD safe via rapidapi`;
  - `CLEAR: GBPUSD safe via rapidapi`;
- no active cron line directly calls the calendar guard; the active runit watcher is the caller.

The calendar guard fails open when both providers are unavailable, so blanking the runtime key does not intentionally block all trading. The durable source fix still needs review and testing.

### Runtime-only mitigation — EXECUTED AND VERIFIED

A reversible mitigation was staged at:

`audits/p4_rapidapi_runtime_disable_ae204a40`

Artifacts:

- `DISABLE_RAPIDAPI_CALENDAR_RUNTIME_V1.sh`
  - SHA-256: `29fa5f954a1c4db3438753712d49dc355293c1991099bda713a090203fd67dbb`;
- `ROLLBACK_RAPIDAPI_CALENDAR_RUNTIME_V1.sh`
  - SHA-256: `c4d3efbc90c92dc3866fd0ce8d95052ba34f2f75f6f41f74ebe61237fc0d0bb5`;
- pre-mutation `.env.runtime` SHA-256:
  - `794b160586e670d08e6a2c9dd0756b57c08b0f7e719005f1d15918df8ac79f48`;
- pre-mutation `.env.runtime` mode: `600`.

The exact file-gated approval was created and verified:

- approval present: YES;
- approval valid: YES;
- approval mode: `600`.

Execution result:

- `APPROVAL_CONSUMED=YES`;
- `RAPIDAPI_RUNTIME_KEY_DECLARATIONS=1`;
- `RAPIDAPI_RUNTIME_KEY_NONEMPTY=0`;
- `RAPIDAPI_RUNTIME_DISABLED=YES`;
- `ENV_RUNTIME_BACKUP_CREATED=YES`;
- `ENV_RUNTIME_EDIT=ATOMIC`;
- `RAPIDAPI_RUNTIME_DISABLE=PASS`;
- independent post-check: `RAPIDAPI_RUNTIME_KEY_DISABLED=YES`;
- rollback backup present: YES;
- exit code: `0`;
- services restarted: NO;
- external API calls made by the package: NO;
- `.env` source file changed: NO.

Current conclusion:

- further RapidAPI fallback calls from future watcher cycles are blocked at runtime because the watcher reloads `.env.runtime` each cycle;
- a call already in flight at mutation time could have completed, but no service restart was required;
- the durable source-code condition remains defective and must be fixed separately on a reviewed branch;
- the rollback remains available at `audits/p4_rapidapi_runtime_disable_ae204a40/ROLLBACK_RAPIDAPI_CALENDAR_RUNTIME_V1.sh`.

## Crontab findings

Live crontab SHA-256:

`2fbbf08b8611ae22ecfc08f9d41a078a6a3437fe1ecfcd6ba931f2f1c99b9a68`

Daily Proof reported:

- canonical crontab verification: FAIL;
- hash match: NO.

Observed live structure:

- former watcher, updater, shadow, closer, heartbeat, and supervisor cron entries are commented with `#MIGRATED_TO_RUNIT`;
- no duplicate active execution was proven from those commented lines;
- Daily Proof remains active;
- runtime-health push remains active every five minutes;
- dividend scanner block remains active and separate.

Canonical verification must be rerun after control-plane stabilization. Do not blindly reinstall cron before reconciling current intended runit/cron ownership.

## Telegram and health-truth findings

Observed transitions included:

- `updater_stale`;
- `shadow_stale`;
- dead-man stale;
- later recovery;
- repeated degradation after recovery.

These alerts cannot all be treated as authoritative because the current supervisor still relies partly on wall-clock/file-mtime freshness. Quiet successful cycles can appear stale, and a restart can touch logs and create a false recovery.

Known deferred suppression defect:

- emitted names use forms such as `watcher_stale`, `updater_stale`, and `shadow_stale`;
- the existing suppression regex expects names such as `watcher_log_stale`;
- intended ship-mode suppression is therefore ineffective.

Do not use Telegram recovery alone as proof that the control plane is healthy.

## Workflow and safety corrections

Every Termux package must:

1. display `audits/ERROR_LOG.md` first;
2. print `ERROR_LOG_REVIEWED=YES`;
3. print `CIRCULAR_ERROR_CHECK=PASS`;
4. use active paths only;
5. avoid recursive scans through runit supervise FIFOs;
6. avoid top-level `exit` that closes the user's Termux shell;
7. avoid interactive approval waits;
8. separate staging, approval, and mutation execution;
9. use compact output and avoid repeating broad audits without contradictory evidence;
10. finish with one next action.

## Ordered next steps

1. Create and verify the two V5 current-boot approval files without executing V5.
2. Execute V5 once and verify exact seven-service ownership under the same standard manager.
3. Run bounded PID/parentage stability checks and continue the endurance gate.
4. Repair the calendar invocation condition and add caching/call-budget controls on a reviewed source branch.
5. Re-run canonical crontab verification.
6. Repair health-transition truth and stale-reason suppression separately.
7. Address Twelve Data call budgeting separately.

## Deferred findings

- root cause of repeated standard-manager death;
- calendar caching and per-day call budget;
- calendar failure/429 observability;
- canonical crontab mismatch;
- health model based on monotonic useful progress;
- stale-reason suppression mismatch;
- Twelve Data quota budgeting;
- external independent dead-man monitoring.