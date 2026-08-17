# BotA Resolved Issues

Last updated: **2026-08-17 UTC**

This file records closed items only. Current blockers belong in `ERRORS.md`, `CONTINUITY_CURRENT.md`, and GitHub issue #9. Detailed historical wording remains available in Git history and dated audits.

## Historical resolved groups

### 2026-04-21 / 2026-04-22

- Yahoo 429 retry storm — RESOLVED.
- `phase=Unknown` market-open contract mismatch — RESOLVED.
- stale watcher lock regression — RESOLVED.

### 2026-05-27

- private Telegram Market Pulse send — RESOLVED.
- daily pulse wrapper and first private live send — RESOLVED for wrapper/send behavior; production cron rollout was intentionally separate.

### 2026-07-10

- watcher pre-journal dedup observability defect — RESOLVED: completed parsed decisions are journaled before delivery gates and delivery hash is marked only after confirmed send.

### 2026-08-09 Package #1

Android wall-clock leakage from audited strategy/event-time semantics — RESOLVED / DEPLOYED / LIVE-PROVEN through inherited trusted server epoch. Calendar signed before/after exclusion windows were corrected. Strategy thresholds and pair scope were unchanged.

### 2026-08-09 Package #2 historical repairs

- stale live `crond` singleton incident — LIVE INCIDENT RESOLVED at that time.
- PID-1-orphaned BotA `runsv` supervisors — LIVE TOPOLOGY RESOLVED at that time.
- watchdog boot persistence/finalizer — DEPLOYED and historically proven.
- PR #87/#88 runtime dependency/pre-market package — DEPLOYED and historically proven.

These historical resolutions do **not** mean the broader control plane remained stable later; the 2026-08-14..17 recurrence is tracked separately in `ERRORS.md` E026.

## 2026-08-16 — PR #108 corrective runtime merge

Status: **RESOLVED / MERGED**

```text
PR108_HEAD_BEFORE_MERGE=3b7ddf84a9546e3b88c65ae5db1598886c82297f
PR108_RUNTIME_MERGE=f36836315526fd2be826e8abff1c333004b64b0c
PR108_STATE=MERGED
```

Resolved within the corrective runtime included current-cycle evidence contracts, generation barrier, crash-consistent Telegram/Supabase delivery ordering, delivery hash consistency/atomicity, evidence retention/recovery, and the modern GREEN/YELLOW Telegram trade-card presentation. No strategy threshold, pair/timeframe, SL/TP/risk, or provider-policy change was authorized by this closure.

## 2026-08-16 — Package 5 transactional phone deployment package

Status: **RESOLVED / MERGED**

```text
PR113_HEAD=2a9d0e444214bf1a3479ff65466850abb6683d84
PR113_MERGE_MAIN=028db6ee5a993869bf33a534c4339475981d9357
PR113_STATE=MERGED
DEPLOYER_RUNTIME_RELEASE_PIN=f36836315526fd2be826e8abff1c333004b64b0c
```

The reviewed deployer remained intentionally pinned to the PR #108 runtime release rather than self-referencing the PR #113 merge SHA.

## 2026-08-16 — Package 6 transactional phone deployment

Status: **DEPLOYMENT RESOLVED / POST-DEPLOY ACCEPTANCE STILL OPEN**

Phone evidence:

```text
REMOTE_MAIN=028db6ee5a993869bf33a534c4339475981d9357
PHONE_PREFLIGHT=PASS
WATCHER_COUNT_BEFORE=1
DEPLOYMENT=PASS
DEPLOY_RC=0
RUNTIME_PARITY=PASS
RUNTIME_FILES_VERIFIED=12
WATCHER_COUNT_AFTER=1
DEPLOY_AUDIT=/data/data/com.termux/files/home/BotA/audits/transactional_phone_deploy_20260816T201256Z_31681
```

The first attempt safely failed before mutation because the deployer did not find `SUPABASE_SERVICE_KEY` in its supported config paths. Production already had the key in local untracked `config/strategy.env`; the existing key was verified as a new Supabase secret and returned HTTP 200 with both current publisher headers and `apikey` only. No secret value was printed or committed. A local ignored `.env.runtime` alias mode `0600` allowed the reviewed deployment to proceed.

### 2026-08-16 — Two stale control-plane file parity mismatches

Status: **RESOLVED ON PHONE / EXACT PARITY REPAIRED**

```text
tools/start_native_service_daemon_watchdog.sh
  expected_and_actual_blob=c383857b7323e1511d71e351a3becd54ca42d682
  mode=755

tools/control_plane_status.py
  expected_and_actual_blob=45e7aa5d5b88668720d48efc009cb376c0109783
  mode=755

CONTROL_PLANE_PARITY_REPAIR=PASS
```

## Not resolved by the entries above

```text
WEEKEND_CONTROL_PLANE_STABILITY=FAIL
LATEST_CONTROL_PLANE_FAILURE=zombie_runsv_count:1
RECURRENT_MANAGER_ORPHAN_CROND_FAILURES=OPEN
PROFITLAB_PENDING_BYTES_AT_FIRST_POSTDEPLOY_GATE=271063
TELEGRAM_WEEKEND_OPERATOR_MESSAGE_VOLUME=89_REPORTED
OPEN_MARKET_THREE_PAIR_LIVE_PROOF=PENDING
PRODUCTION_READY=NO
```

Do not move these items into RESOLVED merely because the runtime temporarily returns to 7/7. Repeated 2026-08-14..17 DEGRADED/RECOVERY evidence proves the stability problem is still open.

Canonical Package 6 evidence: `audits/PACKAGE6_PHONE_DEPLOY_AND_WEEKEND_RUNTIME_FINDINGS_2026-08-17.md`.
