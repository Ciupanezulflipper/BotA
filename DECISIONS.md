# BotA Decisions Register

Last updated: **2026-08-09 UTC**

This file records the decisions that are active now. Older decisions remain available in Git history and dated audit records. When an older decision conflicts with this file, the explicitly superseding decision below controls current work.

## Active locked decisions

### 2026-08-09 — Current production deployment and readiness state

- Status: **LOCKED**
- Approved/deployed runtime release: `f52f326cdbc9e9a16dd60666808a35fb839f10ad`.
- Classification: `DEPLOYED_AND_WEEKEND_VERIFIED`.
- `MONDAY_READY=NO` until a genuine `MARKET_OPEN` cycle proves all current readiness conditions.
- Do not redeploy/restart merely to make persisted cosmetic state look newer.
- Canonical proof: `audits/PHONE_DEPLOYMENT_WEEKEND_PROOF_2026-08-09.md`.

### 2026-08-09 — Live watcher scope supersedes the 2026-04-22 two-pair lock

- Status: **LOCKED / SUPERSEDES 2026-04-22 LIVE-SCOPE DECISION**
- Current production scope:

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

- The old `EURUSD GBPUSD`-only watcher decision is no longer current.
- USDJPY was promoted only after reviewed production-policy/readiness work; do not remove it silently from observability or health scope.
- Do not add more pairs/timeframes without a separate evidence-backed approval.

### 2026-08-09 — Signal frequency is not a readiness criterion

- Status: **LOCKED**
- Do not lower score, ADX, H1/H4/D1, Telegram, cooldown, or eligibility thresholds to manufacture signals.
- Three legitimate rejected/HOLD decisions can satisfy the open-market execution-path proof.
- A Telegram signal is not required for Monday readiness.
- Operational failure must not be reclassified as a strategy rejection.

### 2026-08-09 — Exactly one watcher owner

- Status: **LOCKED**
- Production watcher ownership is runit-only.
- Active direct watcher cron count must remain zero.
- The active physical wrapper is outside the repository worktree:
  `/data/data/com.termux/files/home/.config/bota-sv/bota-watcher/run`.
- Every readiness check must prove current unique ownership; a historical topology snapshot is insufficient.
- Do not restore the migrated direct watcher cron.

### 2026-08-09 — Deployment identity is not the phone Git worktree HEAD

- Status: **LOCKED**
- Phone local checkout currently remains:

```text
branch=deploy/repaired-core-20260802T215531Z
head=4339543551aae2e2bcbf727aefe96e3eb103b665
```

- The deployed release identity is established by immutable approved SHA, bounded deployed-file blob parity, executable modes, runtime configuration, active-wrapper parity, and live-cycle evidence.
- Do not `git reset --hard`, clean the 782 preserved untracked files, or equate worktree cleanliness with deployment correctness.

### 2026-08-09 — Deployment gates are distinct

- Status: **LOCKED**
- Never collapse these states into one claim:

```text
CODE_READY
MERGED_TO_MAIN
DEPLOYMENT_READY
DEPLOYED_TO_PHONE
RUNTIME_PARITY_VERIFIED
LIVE_PIPELINE_VERIFIED
MONDAY_READY
```

- CI/review success does not prove phone deployment.
- `sv status=run` does not prove the correct release or a successful watcher cycle.
- A production deployment must be immutable-SHA pinned, mode-aware, backed up, bounded to the audited manifest, and rollback-capable.

### 2026-08-09 — Server time controls market/lifecycle truth

- Status: **LOCKED**
- Trusted server UTC/epoch is authoritative for market/lifecycle semantics.
- CLOCK_BOOTTIME/monotonic time is authoritative for same-boot cadence/health.
- Android wall clock is currently unsafe (`DRIFT_WARN`, observed drift approximately `-3621s`).
- Fail closed when required time evidence is unavailable or invalid.
- Do not hide the wall-clock warning: cron-style schedules may still be shifted in real time.

### 2026-08-09 — Every watcher cycle needs one authoritative terminal outcome

- Status: **LOCKED**
- Every scheduled watcher cycle must end in an observable terminal outcome from the reviewed enum.
- One cycle ID must remain coherent across gate -> watcher -> reconciler -> ledger.
- Terminal-ledger persistence failure is an operational failure.
- Inner execution failure dominates healthy-looking semantic aggregates and must surface as `INTERNAL_ERROR` or the applicable failure outcome.

### 2026-08-09 — ProfitLab delivery remains independent and cursor state is preserved

- Status: **LOCKED**
- ProfitLab delivery remains independent from Telegram.
- Current worker cadence: once per minute via canonical cron.
- Current preserved state at deployment proof:

```text
cursor_offset=897734
alerts_csv_size=897734
pending_bytes=0
```

- Do not run `profitlab_delivery.py --bootstrap` on the current production state.
- Do not replay historical `alerts.csv` rows during routine deployment.

### 2026-08-09 — Historical replay evidence is frozen

- Status: **LOCKED**
- Do not reacquire or rewrite the canonical June-July historical dataset/replay/matcher/classifier merely because production has evolved.
- Historical evidence remains useful for strategy evaluation but does not substitute for current runtime proof.
- Do not widen matcher tolerances after observing results.

### 2026-08-09 — Open-market readiness gate

- Status: **LOCKED**
- The exactly-one next operational proof is the first genuine `MARKET_OPEN` cycle showing:

```text
EURUSD:M15 current decision present
GBPUSD:M15 current decision present
USDJPY:M15 current decision present
same current cycle identity proven
fresh updater evidence present
fresh shadow evidence present
one authoritative terminal watcher outcome persisted
no active direct watcher cron
no second watcher owner
provider/data failure visible if present
```

- If all three decisions are rejected for legitimate market/strategy reasons, the execution path may still PASS.
- Delivery evidence is evaluated only if a signal genuinely qualifies.

## Separate behavior-changing work requiring its own review

The following must not be mixed into the current readiness observation:

1. **Signal-closer lifecycle** — draft PR #7 is stale. Do not merge it wholesale; salvage only reviewed logic onto current `main` when that work is separately scheduled.
2. **H1/ADX override contract** — fusion/scoring contract mismatch can affect behavior; do not silently repair it during readiness checks.
3. **Session-score clock source** — changing any scoring path from phone wall clock to trusted time can alter scores near session boundaries and therefore requires explicit scoped review.
4. **Legacy/redundant provider refresh cleanup** — reducing provider calls is separate behavior and must not be bundled into a readiness/documentation update.
5. **Device clock correction** — correcting Android/system time is operationally desirable, but verify implications for schedules and do not use local wall clock as trading truth.

## Repository workflow decision

- Status: **LOCKED**
- Never push directly to `main` for normal work.
- Required flow:

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

- Documentation-only changes that advance `main` do not require redeploying an unchanged runtime manifest.

## Superseded decision note

The April 2026 decision that locked the watcher to only EURUSD/GBPUSD and prohibited USDJPY promotion is explicitly superseded by the reviewed and deployed three-pair production candidate. It must not be used by future AI sessions as a current constraint.
