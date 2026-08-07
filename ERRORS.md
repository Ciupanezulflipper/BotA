# BotA Errors and Silent-Failure Register

Last updated: 2026-08-07 17:01 UTC

Purpose: preserve verified failure classes, current open risks, and prevention
rules without repeating broad audits. Detailed current signal evidence is in:

- `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
- `CONTINUITY_CURRENT.md`
- `CHAT_HANDOFF_BOTA.md`
- `audits/ERROR_LOG.md`

## Current verdict — 2026-08-07

```text
PRODUCTION_VALIDATION=FAILED_HISTORICAL
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_CONTROL_PLANE=DEGRADED_6_OWNED_1_ORPHAN
CURRENT_REQUIRED_RUNNING=7_OF_7
CURRENT_ORPHAN_SERVICE=crond
LIVE_WATCHER=RUNNING
SIGNAL_DECISION_ROWS=2507
SIGNAL_BUY_ROWS=466
SIGNAL_SELL_ROWS=959
SIGNAL_HOLD_ROWS=1082
SIGNAL_ACCEPTED_ROWS=110
SIGNAL_REJECTED_ROWS=2397
SIGNAL_REJECTION_RATE≈95.61_PERCENT
ZERO_ENTRY_ROOT_CAUSE=REJECTED_HYPOTHESIS
STRATEGY_MUTATION_ALLOWED=NO_PENDING_FUNNEL_CLASSIFICATION
AUTOMATIC_RECOVERY_REENABLE_ALLOWED=NO
```

The current signal drought cannot be attributed simply to a dead direction
engine. The live corpus contains 1425 BUY/SELL rows. The high-value problem is
now to identify which downstream gates reject valid-entry BUY/SELL candidates
and whether accepted rows reach Telegram delivery.

## Current repository and phone state

```text
GITHUB_MAIN=5e28afafde80c29f57a9be762388dccd91de4734
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=73b2306b5843f3396823ce815e96051abf78cf50
```

## Signal-throughput finding — 2026-08-07

Verified `logs/alerts.csv` schema:

```text
timestamp,pair,tf,direction,score,confidence,entry,sl,tp,provider,rejected,filter_str,reasons
```

Verified decision counts:

```text
TOTAL=2507
HOLD=1082
SELL=959
BUY=466
ACCEPTED=110
REJECTED=2397
```

Frequent filter strings include score thresholds, direction-not-tradeable,
H1-neutral tags, RR text, and `macro6=3`. `H4_D1_oppose` is rare in the current
corpus. `macro6=3` is not yet proven to be a hard reject rather than a tag.

## Closed hypothesis — zero entry caused lost tradeable signals

Direct classification:

```text
ALL_ZERO_ENTRY_SL_TP_ROWS=1014
ALL_VALID_ENTRY_SL_TP_ROWS=1493
MIXED_ROWS=0
ZERO_ROWS_DIRECTION=HOLD_ONLY
ZERO_ROWS_SCORE=0.00_ONLY
ZERO_ENTRY_BUY_SELL_ROWS=0
```

Verdict:

```text
ZERO_ENTRY_IS_HOLD_SYMPTOM_NOT_ROOT_CAUSE
```

Do not trace `entry=0` further as the primary signal defect unless new BUY/SELL
evidence contradicts this result.

## Audit-script schema mistake — 2026-08-07

An exploratory DictReader audit looked up `filter_rejected`, but the actual CSV
field is `rejected`. This caused empty filter-status output in that one audit.
The direction/entry classification from the same audit remains valid, and the
earlier acceptance/rejection counts based on column 11 remain valid.

Prevention:

- print and verify the exact header before writing field-based audits;
- fail if a required CSV field is absent instead of silently using empty values;
- do not promote convenience-script output to evidence until schema validation
  passes.

## Historical closed defect — D1 timeframe mapping

Previous state:

```text
cache/indicators_EURUSD_D1.json
error=tf_mismatch
tf_ok=false
tf_actual_min=0.0
```

Root cause:

```text
tools/build_indicators.py::tf_minutes("D1") returned 0
```

Current deployed mapping:

```text
tf_minutes("D1")=1440
```

## Runtime ownership incident — 2026-08-07

Earlier in the incident two managers existed:

```text
PID 16360 = runsvdir -P .../var/service
PID 31140 = native Termux service-daemon runsvdir .../var/service
service-daemon.pid = 31140
```

PID 16360 initially owned all required BotA supervisors while PID 31140 owned
none. PID 16360 later died, leaving PID-1 orphan supervisors, and PID 31140
progressively reacquired them. Latest observed state is six manager-owned and
one PID-1 orphan (`crond`), with all seven required services running.

Exact caller attribution for the native manager start and exact executor
attribution for PID 16360 termination remain unproven. Do not claim otherwise.

## Closed risk — supervisor wrapper could mutate topology

The active wrapper previously could create `runsvdir` based on a broad process
regex. P7 replaced it with a tracked non-mutating scheduler. The later 2026-08-07
manager incident proves that control-plane safety still requires process-level
ownership verification even after that specific wrapper defect was closed.

## Historical failure classes retained

- control-plane regression to orphaned supervisors;
- duplicate execution ownership between cron/runit/boot paths;
- canonical documentation lagging phone truth;
- strict shell mode terminating the interactive Termux parent;
- recursive scans entering runit FIFOs;
- expected zero matches aborting under `pipefail`;
- wall-clock/monotonic confusion;
- `/proc/uptime` being inaccessible on this Android build;
- service presence being mistaken for useful progress;
- D1 timeframe mismatch;
- active service path being assumed to be the repository path;
- broad runtime work obscuring the actual signal-throughput question;
- oversized terminal evidence packages causing pager/output-loss problems.

## Runtime and signal lessons

- Manager existence does not prove service ownership.
- `sv status` alone does not prove ownership or restart safety.
- PID-1 orphan supervisors can survive manager death.
- A running watcher does not prove acceptable signal throughput.
- A BUY/SELL direction does not prove an accepted or delivered signal.
- A HOLD row may legitimately have entry/SL/TP all zero.
- Filter reason text can contain informational tags; presence alone does not prove
  causal rejection.
- Telegram delivery, dedup, cooldown, Supabase persistence, strategy rejection,
  provider failure, runtime failure, and valid HOLD are distinct outcomes.
- Always verify CSV/schema names before using ad-hoc forensic scripts.

## Operational package rules

- Keep strict shell settings inside a bounded child shell.
- Prefer small pager-proof evidence packages.
- Preserve phone state before Git mutation.
- One package, one evidence domain, one acceptance gate.
- Avoid recursive scans through runit FIFOs.
- Expected zero matches must not abort under `pipefail`.
- Use complete-file replacements for approved code mutations.
- Define rollback before mutation.
- Update canonical documentation with explicit UTC date after each material gate.
- Never push directly to `main`; use branch -> content -> diff -> PR.

## Exactly one next repair/investigation

Do not repair code yet. First classify the 1493 valid-entry rows by `rejected`,
pair, direction, score bucket, and exact `filter_str`, then inspect the 110
accepted rows for Telegram eligibility/delivery. Only the first proven
throughput bottleneck should be changed.
