# BotA Decisions Register

Last updated: **2026-08-10 UTC**

This file records active decisions. Older decisions remain in Git history and dated audits. Explicit supersession here controls current work.

## Active locked decisions

### 2026-08-10 — Replacement runtime architecture after six-model audit

- Status: **LOCKED — GO_BUILD**
- Canonical audit: `audits/REPLACEMENT_RUNTIME_SIX_MODEL_ARCHITECTURE_AUDIT_2026-08-10.md`.
- Preserve the trading engine and strategy behavior. Replace the Android/Termux orchestration layer.
- Selected architecture: constrained **Option A**.

```text
PERSISTENT_PROCESS_COUNT=2
PROCESS_1=MINIMAL_OWNER_RESTARTER
PROCESS_2=LIGHTWEIGHT_PYTHON_ORCHESTRATOR
TRADING_ENGINE_INTEGRATION=EXEC_EXISTING_MODULES_AS_BOUNDED_SUBPROCESSES
ONE_RESURRECTION_AUTHORITY=OWNER_RESTARTER
RUNIT_TARGET=REMOVE_COMPLETELY_AT_CUTOVER
RUNSVDIR_TARGET=REMOVE_COMPLETELY_AT_CUTOVER
BOT_A_CRON_RESTART_AUTHORITY=REMOVE_COMPLETELY
PROFILE_D_PRODUCTION_LAUNCH=FORBIDDEN
BARE_CROND_FALLBACK=REMOVE
STRATEGY_CHANGE=NO
```

- PID existence is not health. The replacement must persist useful-work progress including market data, indicator update, watcher completion, signal decision, closer completion, shadow completion, trusted-clock validation, and external delivery attempt timestamps.
- A live PID with objectively stale required work is a **living zombie** and must result in forced runtime exit followed by restart by the single external owner.
- Every network call and engine subprocess must have bounded deadlines. Infinite retry/blocking paths are forbidden.
- Externally visible side effects require durable intent-before-action semantics and restart reconciliation; blind replay after an unknown outcome is forbidden.
- Android suspend/Doze gaps must not cause replay of stale scans. Revalidate trusted time and candle freshness before resuming.
- Existing trading-engine entrypoints remain behavior-frozen during migration; do not import/refactor them into a new monolithic strategy runtime as part of this package.
- Legacy `runsvdir` death-signal capture is **USEFUL_BUT_NOT_REQUIRED**. It must not restart the historical repair cycle or block replacement development.
- Minimum shadow-live gate: **7 consecutive days**, preferred **10–14 days**, plus parity, fault injection, restart, crash-consistency, and Android unattended tests.
- Cloud remains deferred during proof collection:

```text
CLOUD_NOW=NO
CLOUD_AFTER_STRATEGY_PROOF=YES
```

- Strategy proof and runtime proof are separate. Target >=60% closed-signal win rate must also include positive expectancy and a meaningful clean sample; initial evidence requires at least 100 closed signals, with 200+ preferred for stronger conclusions.
- Exactly one next engineering package: **R1 owner/restarter contract**, tested with a dummy runtime only. No production cutover, strategy change, runit removal, cron removal, or phone startup mutation occurs in R1.

### 2026-08-10 — Previous runit Package #2 path is superseded as target architecture

- Status: **SUPERSEDED FOR FUTURE ARCHITECTURE WORK**
- Prior 2026-08-09 decisions requiring persistent runit/watchdog hardening remain historical evidence of the incident and may still describe the currently deployed legacy phone runtime.
- They no longer define the target architecture or next engineering objective.
- Do not continue PR #89/watchdog-guardian work merely to preserve runit unless new evidence proves the replacement architecture cannot meet its acceptance contract.
- Until cutover, the existing phone runtime must not be destructively altered outside an explicit migration/deployment gate.

### 2026-08-09 — Deployed production release after Package #1

- Status: **HISTORICAL / LEGACY-RUNTIME CONTEXT**
- Current deployed runtime release at that checkpoint: `8728de6b5a2ed0f4647374ef4fa6ed72f9eb03c0`.
- Package #1 (`Clock & Session Time`) was **PASS**: merged, hash-pinned, deployed, byte-parity verified, and live-proven.
- Package #2 (`Pre-Market Production Integrity`) was pending despite successful live control-plane repairs.
- Canonical dated proof: `audits/PACKAGE1_CLOCK_AND_PACKAGE2_CONTROL_PLANE_2026-08-09.md`.

### 2026-08-09 — One trusted strategy/event instant per watcher cycle

- Status: **LOCKED**
- `BOTA_SERVER_EPOCH` is authoritative for market/session/economic-event semantics within a production watcher cycle.
- Nested market gates and scorer/calendar/news consumers must reuse the inherited trusted epoch rather than independently reading Android wall clock or establishing unrelated `now` values.
- CLOCK_BOOTTIME/monotonic remains authoritative for elapsed-duration health, cadence, cooldown, and same-boot freshness.
- Fail closed when trusted strategy/event time is required but unavailable.
- Package #1 changed the time source, not score thresholds or session-score values.

### 2026-08-09 — Calendar before/after semantics are directional

- Status: **LOCKED**
- For `minutes_away = event_time - now`, positive values mean before the event and negative values mean after it.
- The prior sign inversion was fixed in Package #1.
- Current configured windows retain their intended values; only the direction/application bug was corrected.

### 2026-08-09 — Service liveness and service ownership are separate health dimensions

- Status: **HISTORICAL INCIDENT RULE**
- `sv status=run`, a live wrapper PID, or continuing cron jobs are not sufficient proof of a healthy legacy runit control plane.
- Historical readiness/control-plane checks separately established one manager, seven owned supervisors, seven running services, zero PID-1 orphan supervisors, and zero duplicate service rows.
- This distinction remains useful forensic evidence, but the replacement runtime uses useful-work progress rather than runit ownership topology as its primary health contract.

### 2026-08-09 — Stale live singleton child is not the same as stale dead pidfile

- Status: **LOCKED FORENSIC RULE**
- A pidfile/resource lock must not be deleted merely because a supervisor cannot start its service.
- Before terminating or removing anything, prove whether the recorded owner PID is alive, its command identity, and its parent/ownership lineage.
- Exact historical incident: stale live `crond` PID 4107, PPID 1, held `crond.pid` while current manager-owned `runsv crond` retried replacements.

### 2026-08-09 — Current production scope

- Status: **LOCKED**

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

- Do not add/remove pairs or loosen thresholds as an operational recovery mechanism.

### 2026-08-09 — Signal frequency is not a readiness criterion

- Status: **LOCKED**
- Do not lower score, ADX, H1/H4/D1, Telegram, cooldown, or eligibility thresholds to manufacture signals.
- Operational failure must not be reclassified as strategy rejection.

### 2026-08-09 — Deployment identity is not phone Git HEAD

- Status: **LOCKED**

```text
PHONE_LOCAL_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_LOCAL_HEAD=4339543551aae2e2bcbf727aefe96e3eb103b665
```

- Deployed identity requires immutable approved SHA, bounded file blob/mode parity, active-wrapper parity, runtime config, and live proof.
- Do not reset/clean the phone merely to make its checkout resemble production.

### 2026-08-09 — Deployment/readiness gates remain distinct

- Status: **LOCKED**

```text
CODE_READY
MERGED_TO_MAIN
DEPLOYMENT_READY
DEPLOYED_TO_PHONE
RUNTIME_PARITY_VERIFIED
LIVE_PIPELINE_VERIFIED
SHADOW_ACCEPTANCE
CUTOVER_READY
STRATEGY_EVIDENCE_READY
```

- Passing an earlier gate does not imply later gates.

### 2026-08-09 — Every watcher cycle needs one authoritative terminal outcome

- Status: **LOCKED**
- Every scheduled watcher cycle must end in an observable terminal outcome.
- One cycle ID remains coherent across gate -> watcher -> reconciler -> ledger.
- Terminal-ledger persistence failure is operational failure.

### 2026-08-09 — ProfitLab state is independent and preserved

- Status: **LOCKED**

```text
cursor_offset=897734
alerts_csv_size=897734
pending_bytes=0
```

- Do not run `profitlab_delivery.py --bootstrap` on current production.
- Do not replay historical alerts during routine deployments/recovery.

## Separate behavior-changing work

Do not mix these into the replacement-runtime migration:

1. **Signal-closer lifecycle** — separate behavior review.
2. **H1/ADX override contract** — separate strategy behavior review.
3. **Legacy/redundant provider refresh cleanup** — separate behavior/performance change.
4. **Compact state-schema normalization** — deferred bookkeeping unless operationally material.
5. **Android system-clock correction** — separate device task; trusted server epoch remains trading truth.
6. **Threshold/pair/timeframe optimization** — forbidden during runtime migration.

## Repository workflow decision

- Status: **LOCKED**
- Normal flow:

```text
inspect current truth
-> bounded branch
-> complete-file changes
-> verify exact diff
-> PR
-> exact-head static/review gates
-> resolve findings
-> merge
-> separate deployment gate when runtime files changed
```

Never push normal work directly to `main`.
