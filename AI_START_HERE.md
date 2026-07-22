# BotA AI Start Here

Last updated: 2026-07-22

Read this before proposing BotA commands, code, cron, service, strategy, or deployment changes.

## Evidence and scope rules

Classify material claims as VERIFIED, ASSUMED, or UNKNOWN. Do not promote a failed acceptance criterion because adjacent behavior worked, and do not fail a healthy recovery because process IDs changed.

Current work is Phase 5 observability and decision-data collection. Do not change strategy, thresholds, pairs, scoring, SL/TP, filters, PR #7, DeepSource, Supabase signal semantics, or `main` directly.

Every Termux package must:

1. display `$HOME/BotA/audits/ERROR_LOG.md`;
2. print `ERROR_LOG_REVIEWED=YES`;
3. print `CIRCULAR_ERROR_CHECK=PASS`;
4. use compact active-path checks;
5. avoid supervise FIFOs and broad historical scans;
6. avoid top-level exits that close Termux;
7. avoid blocking interactive approval;
8. separate staging, approval, mutation, rollback, and verification;
9. end with exactly one next action.

Additional mandatory rules:

- do not use `/proc/uptime` on this Android build;
- changed PIDs are restart events, not failures by themselves;
- use trusted server/provider UTC for market semantics;
- use monotonic time for same-boot cadence and health;
- Android/ship wall time is display-only;
- when one correctly owned service child is absent, take one targeted bounded recovery sample before proposing mutation;
- do not rerun V5 or a broad seven-service repair while one-manager ownership remains healthy.

## Phase state

1. Single execution source and cron hygiene — COMPLETE.
2. Runtime survival controls — COMPLETE.
3. Ship-time safety proof — COMPLETE.
4. Reboot and functional recovery proof — COMPLETE.
5. Monday readiness and decision-data collection — NOT STARTED.

Completed: **4/5**. Remaining: **1/5**.

## Final Phase 4 state

Boot ID:

`ae204a40-c3ff-4c4e-abc2-39696b867781`

Final marker:

```text
PHASE4_FUNCTIONAL_RECOVERY=PASS MANAGER_COUNT=1 MANAGER_PID=31330 OWNED=7/7 RUNNING=7/7 WRAPPER_CHAIN=7/7 ORPHANED=0 DOWN_MARKERS=0 LIVE_CROND_COUNT=1 CROND_SUPERVISED=YES RAPIDAPI_DISABLED=YES
```

Verified topology at the final sample:

- exactly one standard Termux `runsvdir` manager;
- manager PID `31330`, PPID 1;
- all seven supervisors owned by that manager;
- all seven services and wrapper chains running;
- zero orphaned supervisors;
- zero `down` markers;
- one supervised `crond -n -s`;
- RapidAPI runtime key declared once and empty;
- no V5 rerun or rollback required.

The manager changed during the same boot from PID `4090` to `20630` and later to `31330`. This is not a Phase 4 failure because each replacement rebuilt a valid single control plane.

One snapshot found the crond supervisor without a child. A targeted audit then proved automatic recovery:

- crond runsv PID `24619`, PPID `31330`;
- live crond PID `13521`, PPID `24619`;
- crond and crond/log both reported `run`;
- no manual restart occurred.

Classification:

`TARGETED_CROND_AUDIT=CROND_RECOVERED_DURING_AUDIT`

Full evidence:

`docs/PHASE4_FUNCTIONAL_RECOVERY_2026-07-22.md`

## Known audit mistakes that must not recur

- fixed-PID stability was incorrectly used as the endurance criterion;
- `/proc/uptime` caused a permission failure;
- the user's explicit current date/time was misinterpreted and produced an unnecessary wait;
- a transient crond child absence was escalated before bounded recovery;
- continuity was not updated quickly enough after runtime truth changed;
- a dead-man alert claimed server UTC `14:13`, last shadow `15:10`, and `198min` stale, an impossible ordering.

Read `ERRORS.md` before designing any package.

## Efficient workflow

### Gate A — one-line functional snapshot

Check:

- manager count;
- seven manager-owned supervisors;
- seven running wrapper chains;
- orphan count;
- one supervised crond;
- API protection;
- useful-progress markers.

If all pass, stop infrastructure diagnosis.

### Gate B — targeted diagnostic only

Inspect only the failed service or data path. Do not run a full control-plane audit for a single-service finding.

### Gate C — bounded automatic-recovery sample

When ownership is correct but a child is absent, take one short targeted resample. Classify automatic recovery, persistent unavailability, or structural ownership failure.

### Gate D — staged mutation

Mutation requires persistent failure, a narrow cause/hypothesis, backup, rollback, separate typed approval, and independent verification.

## RapidAPI incident

The calendar fallback leak remains blocked at runtime:

- `RAPIDAPI_CALENDAR_KEY` is declared once and empty in `.env.runtime`;
- future watcher cycles cannot use the RapidAPI fallback;
- persistent `.env` is unchanged.

The durable source-condition fix, caching, daily call budget, and Twelve Data quota work remain deferred.

## Phase 5 objective

Do not force a signal.

Prove that every scheduled live-market cycle produces one auditable result:

1. a complete parsed decision recorded in `logs/alerts.csv`; or
2. an explicit pre-fusion skip reason in active runtime logs.

The evidence must distinguish:

- trusted-clock unavailable;
- stale or missing raw candle cache;
- pause guard;
- news gate;
- calendar block;
- fusion empty/fail-closed;
- parse failure;
- filter rejection/HOLD;
- accepted signal;
- Telegram score, tier, cooldown, dedup, or connectivity gate.

Only after clean decision-data collection may the strategy be judged too restrictive.

## Deferred findings

- root cause of repeated standard-manager replacement;
- dead-man time-source and future/negative-age protection;
- stale-reason suppression mismatch;
- canonical crontab verification/hash mismatch;
- durable calendar source condition and caching;
- Twelve Data budgeting;
- external independent dead-man monitoring;
- strategy review after Phase 5 evidence.

## Files to read

- `CONTINUITY_CURRENT.md`
- `docs/PHASE4_FUNCTIONAL_RECOVERY_2026-07-22.md`
- `docs/RUNTIME_HANDOFF_V5_RESULT_2026-07-20.md`
- `docs/RUNTIME_CHECKPOINT_2026-07-20.md`
- `ERRORS.md`
- GitHub issue #9
- draft PR #10

## Exactly one next phase

Begin Phase 5 with one read-only, bounded decision-path and useful-progress baseline. Do not mutate runtime configuration or strategy.
