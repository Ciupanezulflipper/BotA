# BotA Decisions Register

Last updated: **2026-08-09 UTC**

This file records active decisions. Older decisions remain in Git history and dated audits. Explicit supersession here controls current work.

## Active locked decisions

### 2026-08-09 — Deployed production release after Package #1

- Status: **LOCKED**
- Current deployed runtime release: `8728de6b5a2ed0f4647374ef4fa6ed72f9eb03c0`.
- Package #1 (`Clock & Session Time`) is **PASS**: merged, hash-pinned, deployed, byte-parity verified, and live-proven.
- Package #2 (`Pre-Market Production Integrity`) is **PENDING** despite successful live control-plane repairs.
- `MONDAY_READY=NO` until Package #2 passes and a genuine open-market three-pair cycle passes.
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

- Status: **LOCKED**
- `sv status=run`, a live wrapper PID, or continuing cron jobs are not sufficient proof of a healthy control plane.
- Every readiness/control-plane check must separately establish:

```text
one native runsvdir manager
one runsv supervisor per required service
all seven required supervisors owned by that manager
all seven services running
zero PID-1 orphan supervisors
zero duplicate service rows
singleton child/resource owner correct where applicable
```

- The Package #2 incident proved this distinction: cron jobs were executing while the current manager-owned `runsv crond` could not own the live daemon.

### 2026-08-09 — Stale live singleton child is not the same as stale dead pidfile

- Status: **LOCKED**
- A pidfile/resource lock must not be deleted merely because the current supervisor cannot start its service.
- Before terminating or removing anything, prove whether the recorded owner PID is alive, its command identity, and its parent/ownership lineage.
- Exact incident: stale live `crond` PID 4107, PPID 1, held `crond.pid` while current manager-owned `runsv crond` PID 24583 retried replacements.
- The accepted live repair was: quiesce current restart loop -> verify stale daemon identity -> terminate stale daemon -> let current `runsv` start one replacement -> verify replacement parentage/stability.
- Package #2 must automate this class safely rather than rely on manual operator repair.

### 2026-08-09 — Persistent watchdog remains a Package #2 gate

- Status: **LOCKED**
- The watchdog source matching GitHub and a one-shot RC 0 are not equivalent to persistent recovery.
- Current phone boot launcher explicitly has `RUNSVDIR_GUARD_START=DISABLED`.
- Package #2 must prove a single-instance persistent watchdog after Termux service-manager startup without creating a second manager/supervisor generation.
- It must recover or safely classify manager loss, orphaned `runsv`, down services, duplicate supervisors, stale dead pidfiles, and live stale singleton-child/resource-owner conditions.

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

- The old EURUSD/GBPUSD-only scope is superseded.
- Do not add/remove pairs or loosen thresholds as an operational recovery mechanism.

### 2026-08-09 — Signal frequency is not a readiness criterion

- Status: **LOCKED**
- Do not lower score, ADX, H1/H4/D1, Telegram, cooldown, or eligibility thresholds to manufacture signals.
- Three legitimate rejected/HOLD decisions can satisfy the final open-market execution-path proof.
- A Telegram signal is not required.
- Operational failure must not be reclassified as strategy rejection.

### 2026-08-09 — Exactly one watcher owner

- Status: **LOCKED**
- Production watcher ownership is runit-only.
- Active direct watcher cron count must remain zero.
- Active physical wrapper:
  `/data/data/com.termux/files/home/.config/bota-sv/bota-watcher/run`.
- Every readiness check must prove current unique ownership.

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
PRE_MARKET_PRODUCTION_INTEGRITY
OPEN_MARKET_THREE_PAIR_PROOF
MONDAY_READY
```

- Passing an earlier gate does not imply later gates.
- Package #2 live repair does not imply Package #2 persistent hardening is complete.

### 2026-08-09 — Every watcher cycle needs one authoritative terminal outcome

- Status: **LOCKED**
- Every scheduled watcher cycle must end in an observable terminal outcome.
- One cycle ID remains coherent across gate -> watcher -> reconciler -> ledger.
- Terminal-ledger persistence failure is operational failure.

Latest Package #1 live proof:

```text
cycle_id=b32a66a6-1a91-4b61-b759-c32851cbae6b:144452448476926
terminal_outcome=MARKET_CLOSED
market_reason=MARKET_CLOSED_SUNDAY
time_source=server_epoch
```

### 2026-08-09 — ProfitLab state is independent and preserved

- Status: **LOCKED**

```text
cursor_offset=897734
alerts_csv_size=897734
pending_bytes=0
```

- Do not run `profitlab_delivery.py --bootstrap` on current production.
- Do not replay historical alerts during routine deployments/recovery.

### 2026-08-09 — Package #2 acceptance contract

- Status: **LOCKED**
- Before persistent phone changes, Package #2 must have isolated fault tests for at least:

```text
manager loss
PID-1 orphaned runsv handoff
single service down
dead stale pidfile
live stale singleton child/resource owner
duplicate supervisor
multiple manager attempt
watchdog duplicate attempt
release/blob/config drift
missing/stale updater or shadow/data readiness
```

- The production implementation must preserve one native manager and one owner per required service.
- Strategy behavior is out of scope.

### 2026-08-09 — Final open-market readiness gate

- Status: **LOCKED**
- After Package #2 passes, the first genuine `MARKET_OPEN` cycle must show:

```text
EURUSD:M15 current decision present
GBPUSD:M15 current decision present
USDJPY:M15 current decision present
same current cycle identity proven
fresh updater/data evidence
fresh shadow evidence
one authoritative terminal watcher outcome
trusted server time
no active direct watcher cron
no second watcher owner
7/7 correctly owned and running
```

- Three legitimate rejects are acceptable.
- Delivery evidence is checked only if a signal genuinely qualifies.

## Separate behavior-changing work

Do not mix these into Package #2:

1. **Signal-closer lifecycle** — draft PR #7 is stale; do not merge wholesale.
2. **H1/ADX override contract** — separate strategy behavior review.
3. **Legacy/redundant provider refresh cleanup** — separate behavior/performance change.
4. **Compact state-schema normalization** — deferred bookkeeping unless it becomes operationally material.
5. **Android system-clock correction** — separate operational/device task; trusted server epoch remains trading truth.

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