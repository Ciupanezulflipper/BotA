# BotA Current Continuity State

Last updated: 2026-07-22

This is the compact current handoff. Historical detail remains in `CONTINUITY.md`. Phase 4 closure and the corrected recovery model are recorded in `docs/PHASE4_FUNCTIONAL_RECOVERY_2026-07-22.md`. V5 ownership-transfer detail remains in `docs/RUNTIME_HANDOFF_V5_RESULT_2026-07-20.md` and GitHub issue #9.

## Operating rules

- Reliability and observability work only until Phase 5 decision-data collection is complete.
- Strategy, thresholds, pairs, scoring, SL/TP, filters, PR #7, DeepSource, and Supabase signal semantics remain frozen.
- No direct push to `main`.
- Every Termux package displays `audits/ERROR_LOG.md`, prints `ERROR_LOG_REVIEWED=YES` and `CIRCULAR_ERROR_CHECK=PASS`, uses active paths only, and ends with exactly one next action.
- Mutations require separate staging, approval, execution, rollback, and independent verification.
- A changed PID is a restart event, not a failure by itself. Judge runtime health by functional ownership, liveness, useful progress, and automatic recovery.
- Never depend on `/proc/uptime` on this Android build.
- Ship/Android wall time is display-only. Use trusted server/provider UTC for market semantics and monotonic time for same-boot cadence and health.

## Phase state

1. Single execution source and cron hygiene — COMPLETE.
2. Runtime survival controls — COMPLETE.
3. Ship-time safety proof — COMPLETE.
4. Reboot and functional recovery proof — COMPLETE.
5. Monday readiness and decision-data collection — NOT STARTED.

Completed: **4/5**. Remaining: **1/5**.

## Phase 4 closure

Final marker:

```text
PHASE4_FUNCTIONAL_RECOVERY=PASS MANAGER_COUNT=1 MANAGER_PID=31330 OWNED=7/7 RUNNING=7/7 WRAPPER_CHAIN=7/7 ORPHANED=0 DOWN_MARKERS=0 LIVE_CROND_COUNT=1 CROND_SUPERVISED=YES RAPIDAPI_DISABLED=YES
```

Verified:

- unchanged boot ID `ae204a40-c3ff-4c4e-abc2-39696b867781`;
- exactly one standard Termux `runsvdir` manager;
- manager PID `31330`, PPID 1 at the final sample;
- all seven runsv supervisors owned by that manager;
- all seven services and wrapper chains running;
- zero orphaned supervisors;
- zero `down` markers;
- exactly one supervised `crond -n -s`;
- RapidAPI runtime disable preserved;
- V5 rerun not required;
- rollback not required;
- no runtime mutation performed by the final audits.

## Recovery evidence and corrected interpretation

The standard manager changed more than once during the same boot: PID `4090`, then `20630`, then `31330`.

This does not invalidate Phase 4. Each later manager reconstructed a single manager-owned service tree without duplicate or orphaned supervisors.

One snapshot captured the manager-owned crond supervisor without a live crond child and returned `6/7`. A targeted audit then proved automatic runit recovery:

- crond runsv PID `24619`, PPID `31330`;
- live crond PID `13521`, PPID `24619`;
- command `crond -n -s`;
- crond and crond/log both reported `run`;
- active spool `u0_a414`, mode `600`, UID `10414`;
- no manual repair was performed.

Classification:

`TARGETED_CROND_AUDIT=CROND_RECOVERED_DURING_AUDIT`

The earlier requirement for identical PIDs over 12 hours was rejected as an invalid acceptance criterion. Phase 4 proves functional recovery, not permanent PID identity.

## New errors and findings

- `/proc/uptime` is inaccessible and caused a read-only package to fail with `PermissionError`.
- The user-provided current date/time was misinterpreted, causing an unnecessary additional wait instruction.
- Exact PID matching incorrectly converted healthy runit recovery into an audit failure.
- A transient crond-child absence was escalated before allowing a bounded automatic-recovery sample.
- A dead-man alert reported server UTC `14:13` but last shadow `15:10`, making the claimed `198min` stale duration impossible and untrustworthy.
- Documentation lagged runtime truth and still named manager PID `4090` after later recovery evidence.

Full analysis and prevention rules:

`docs/PHASE4_FUNCTIONAL_RECOVERY_2026-07-22.md`

## Efficient workflow

Use a four-gate protocol:

1. **Functional snapshot:** manager, seven supervisors, seven wrappers, orphan count, supervised crond, API protection, useful progress.
2. **Targeted diagnostic:** inspect only the failing service or data path.
3. **Bounded recovery resample:** when ownership is correct but a child is temporarily absent, allow one short recovery sample before proposing mutation.
4. **Staged mutation:** only for a persistent failure, with cause/hypothesis, backup, rollback, separate approval, and independent verification.

Do not rerun V5, broad seven-service repair, or rollback while the functional invariants remain healthy.

## RapidAPI quota mitigation

The calendar fallback leak remains blocked at runtime:

- `RAPIDAPI_CALENDAR_KEY` is declared once and empty in `.env.runtime`;
- RapidAPI fallback cannot run in future watcher cycles;
- persistent `.env` remains unchanged;
- rollback backup remains available.

The durable calendar source condition, caching, daily call budget, and Twelve Data budgeting remain deferred.

## Phase 5 objective

Do not force a signal or lower thresholds.

Prove that every scheduled live-market cycle produces one auditable outcome:

1. a complete parsed decision recorded in `logs/alerts.csv`; or
2. an explicit pre-fusion skip reason in active runtime logs.

This must distinguish:

- valid quiet/HOLD behavior;
- stale or missing market data;
- trusted-clock failure;
- news/calendar blocking;
- fusion/parse failure;
- filter rejection;
- Telegram delivery gating;
- a genuinely accepted signal.

Only after clean decision-data collection may strategy restrictiveness be evaluated.

## Deferred findings

- root cause of repeated standard-manager replacement;
- dead-man time-source and negative/future-age protection;
- stale-reason suppression mismatch;
- canonical crontab verifier/hash mismatch;
- durable calendar guard fix, caching, and call budget;
- Twelve Data budgeting;
- external independent dead-man monitoring;
- strategy/threshold review after Phase 5 evidence.

## Exactly one next phase

Begin Phase 5 with a read-only, bounded decision-path and useful-progress baseline. Do not mutate strategy or runtime configuration.
