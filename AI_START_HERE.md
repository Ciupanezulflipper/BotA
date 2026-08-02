# BotA AI Start Here

Last updated: 2026-08-02

Read this before proposing BotA commands, code, cron, service, strategy,
notification, provider, or deployment changes.

## Current truth

The July 26 native-manager closure was valid at that timestamp, but the later
one-week production validation failed.

Current authoritative status:

```text
PRODUCTION_VALIDATION=FAILED
FINAL_ROLLBACK_CONTROL_PLANE=PASS_AT_RECORDED_TIMESTAMP
AUTOMATIC_TOPOLOGY_RECOVERY=DISABLED
CURRENT_PHONE_TOPOLOGY=UNKNOWN_UNTIL_FRESH_NARROW_PROOF
PR24_MERGE_ALLOWED=NO
STRATEGY_MUTATION_ALLOWED=NO
```

Read `audits/INCIDENT_2026-08-01_VALIDATION_FAILURE.md` before treating the
service-manager or watchdog work as closed.

## Scope lock

Current work is limited to:

- runtime reliability;
- data integrity;
- provider-budget accounting;
- Telegram/status correctness;
- repository/runtime convergence;
- observability and signal-lifecycle proof.

Do not change strategy, thresholds, pairs, scoring, ADX, H1/D1 rules, volatility
or macro filters, dedup behavior, SL/TP, PR #7, or Supabase signal semantics to
manufacture signals.

Never push directly to `main`.

## Evidence classification

Classify material claims as:

- VERIFIED: current direct evidence proves the claim;
- ASSUMED: plausible but not proven;
- UNKNOWN: insufficient evidence; do not mutate from it.

A historical PASS does not override a later verified regression. A current
recovery snapshot does not erase the preceding failure. A PID change alone is a
restart event, not proof of failure.

## Mandatory Termux package rules

Every package must:

1. display `$HOME/BotA/audits/ERROR_LOG.md`;
2. run `set -Eeuo pipefail` only inside a bounded child script;
3. preserve the interactive parent shell;
4. answer one narrow question;
5. inspect whitelisted active files and logs only;
6. avoid runit supervise FIFOs and broad recursive scans;
7. treat expected zero matches safely;
8. revalidate exact targets immediately before mutation;
9. separate preflight, backup, rollback, mutation, and independent verification;
10. end with exactly one next action.

Do not use `/proc/uptime` on this Android build.

## Time semantics

- Trusted provider/server UTC controls market-session and candle semantics.
- Monotonic time controls same-boot cadence, cooldowns, and health.
- Android/ship wall time is display-only.
- Reject negative or future stale ages.
- Print the exact timestamps used in any age calculation.

## Correct runit ownership proof

`supervise/pid` is the supervised service process, not the `runsv` supervisor.

Resolve each service as:

```text
service PID -> PPID -> runsv supervisor -> supervisor PPID/cwd/state/command
```

A manager process and matching pidfile do not prove service ownership.
`sv status` does not prove parentage or restart capability.

## August 1 validation failure

Verified failures included:

- `owned=0/7`, `running=7/7`, `orphaned=7` during production operation;
- temporary required-service counts below seven;
- canonical crontab verification failure;
- phone checkout and GitHub `main` divergence;
- documented watchdog topology not matching the phone;
- configured service-daemon executable unavailable;
- repeated Termux restarts while a continuous `runsvdir` guard was active.

The guard and watchdog were stopped. Automatic topology recovery was disabled.
The recorded final rollback state was one manager, seven owned/running services,
zero orphans, and `control_plane_rc=0`.

Do not re-enable automatic recovery without a new bounded design and
failure-injection proof.

## Repository containment

PR #24 is contaminated and non-mergeable. Its description says three files, but
its actual scope expanded to unrelated runtime, provider, documentation,
notification, and test changes on an old divergent base.

Rules:

- do not merge PR #24;
- do not deploy from PR #24;
- do not resolve its analyzer findings by blindly editing the same branch;
- salvage only one behavior at a time from current `main`;
- use complete-file replacements and focused tests;
- keep documentation-only, runtime, provider, and notification work separate.

The clean documentation containment branch is:

```text
repair/production-validation-truth-20260802
```

## Latest data discovery

The latest supplied Termux discovery is complete and read-only:

```text
LOCAL_STATUS_DATA_DISCOVERY_COMPLETE=YES
RUNTIME_MUTATION_PERFORMED=NO
GIT_CHANGED=NO
```

Do not request another broad file/cache dump.

The highest-priority concrete data defect from that evidence is:

```text
cache/indicators_EURUSD_D1.json
error=tf_mismatch
tf_ok=false
tf_actual_min=0.0
weak=true
```

Weekend candle age alone is not enough to declare failure. The explicit D1
mismatch must be reproduced through the active fetch/build path.

## Efficient diagnostic gates

### Gate A — repository and phone safety

Before any phone Git operation, identify and preserve every local modification.
Do not reset, checkout, merge, pull, or overwrite an unclassified dirty worktree.

### Gate B — control plane

Only when current runtime evidence is needed, prove one intended manager, seven
owned/running supervisors, zero orphans/invalid/duplicates, supervised crond,
and the actual boot launcher. Do not assume a watchdog exists.

### Gate C — active data path

Prove exact provider response, timestamps, granularity, row count, cache writer,
and indicator builder for one pair/timeframe. Do not mix multiple providers or
all timeframes in one reproduction.

### Gate D — decision integrity

After data is valid, classify a watcher cycle as valid HOLD/rejection, eligible
signal, send failure, persistence failure, or infrastructure failure. Confirm the
full decision record exists before dedup.

### Gate E — lifecycle

When a real signal becomes ACTIVE, verify Telegram, Supabase, closer execution,
and CLOSED/CANCELLED transition with result pips.

### Gate F — mutation

Mutation requires persistent failure, narrow cause, exact target state, backup,
rollback, explicit authorization, and independent post-change verification.

## Files to read

1. `CONTINUITY_CURRENT.md`
2. `audits/INCIDENT_2026-08-01_VALIDATION_FAILURE.md`
3. `audits/ERROR_LOG.md`
4. `ERRORS.md`
5. GitHub issue #9

## Exactly one next action

From current `main`, create a focused code branch that reproduces and repairs the
EURUSD D1 `tf_mismatch`; do not touch runtime processes, strategy, Telegram, or
the production phone checkout in that package.