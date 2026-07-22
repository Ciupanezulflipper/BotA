# BotA Errors and Silent-Failure Register

Last updated: 2026-07-22

Purpose: record runtime failures, audit mistakes, and prevention rules that must not be rediscovered from scratch.

Detailed current evidence:

- `docs/RUNTIME_CHECKPOINT_2026-07-20.md`
- `docs/RUNTIME_HANDOFF_V5_RESULT_2026-07-20.md`
- `docs/PHASE4_FUNCTIONAL_RECOVERY_2026-07-22.md`
- GitHub issue #9

## E-001 — Closer lifecycle freeze

Status: structurally mitigated; continue monitoring.

History:

- stale ACTIVE Supabase signals blocked new per-pair signals through dedup;
- `tools/run_signal_closer_live.sh` and trusted-clock lifecycle handling were added.

Detection:

- closer useful-progress age;
- ACTIVE signal count;
- oldest ACTIVE signal age;
- ACTIVE -> CLOSED/CANCELLED transition proof.

## E-002 — Runtime crontab wipe

Status: restored previously; canonical hash mismatch remains deferred.

History:

- live crontab lost BotA runtime lines;
- Daily Proof survived and produced false comfort while the signal factory was unscheduled;
- canonical template, installer, and verifier were added.

Current evidence:

- live crontab SHA-256: `2fbbf08b8611ae22ecfc08f9d41a078a6a3437fe1ecfcd6ba931f2f1c99b9a68`;
- Daily Proof reports canonical verification failure and hash mismatch;
- migrated runit jobs are commented in cron and were not proven active duplicates.

Prevention:

- verify intended cron/runit ownership before reinstalling;
- compare canonical block hash;
- preserve unrelated dividend-scanner cron;
- prove useful progress after any restore.

## E-003 — Incomplete or misleading Daily Proof

Status: OPEN.

Current issue:

- Daily Proof reports more runtime evidence than before;
- Telegram and supervisor health still depend partly on mixed wall-clock, server-UTC, and file-mtime inputs;
- a quiet successful cycle can be classified stale;
- restart log touches can look like recovery;
- a 2026-07-22 alert claimed server UTC `14:13`, last shadow `15:10`, and stale age `198min`, which is impossible because the alleged last shadow was in the future.

Prevention:

- use one trusted UTC source for cross-boot/event timestamps;
- use monotonic useful-progress markers for same-boot freshness;
- reject future/negative ages;
- print the exact age inputs in diagnostics;
- separate service presence from useful progress;
- never treat one RECOVERY notification as proof of structural health.

## E-004 — Termux/Android runtime fragility

Status: functionally mitigated for Phase 4; root cause remains open.

Known risks:

- Android can replace the standard `runsvdir` manager during the same boot;
- a manager restart can recreate child supervisors and wrappers with new PIDs;
- a child service can be temporarily absent while runit is recovering it;
- mobile network and ship conditions can interrupt providers and Telegram.

Current evidence:

- reboot recovery passed;
- V5 ownership handoff passed under manager PID `4090`;
- later healthy trees appeared under manager PIDs `20630` and `31330` on the same boot;
- final functional closure passed with one manager, seven owned supervisors, seven wrappers, zero orphans, and one supervised crond.

Prevention:

- verify exactly one standard manager;
- verify every runsv parent and wrapper chain;
- treat PID replacement as a restart event, not an automatic failure;
- use wake lock and Termux:Boot;
- judge recovery by functional invariants and useful progress.

## E-005 — Network / TLS / Telegram failure

Status: observed historically; transient.

Prevention:

- distinguish network/TLS failure from BotA logic failure;
- check Telegram, Supabase, and provider connectivity;
- rate-limit transition alerts.

## E-006 — API/data-provider degradation

Status: active.

Known risks:

- Twelve Data credit exhaustion;
- Global Economic Calendar API quota exhaustion;
- Yahoo 429/rate limiting;
- OANDA/cache gaps;
- server-clock source unavailable.

Current evidence:

- Twelve Data warning: 600/800 credits;
- Global Economic Calendar API BASIC quota: 100% consumed;
- runtime RapidAPI key is now declared once and empty in `.env.runtime`.

Prevention:

- per-provider call budgets;
- explicit quota/429 logging;
- cache reuse;
- failover with bounded retries;
- do not conflate separate provider quotas.

## E-007 — ProfitLab observability gap

Status: partially closed.

- BotA runtime health is pushed to Supabase.
- ProfitLab must distinguish quiet/no-signal from dead/offline runtime.
- Health truth still depends on fixing false stale/recovery classification.

## E-008 — Dead standard runsvdir with orphaned supervisors

Status: repaired; monitor for recurrence.

Historical failure:

- standard manager disappeared;
- all six BotA runsv supervisors and runsv crond remained under PID 1;
- `sv status` alone appeared healthy even though ownership and restart capability were broken.

Verified recovery:

- V5 restored exactly one standard Termux manager;
- all seven supervisors were transferred beneath it;
- later manager replacements rebuilt a valid single control plane;
- final Phase 4 functional recovery passed.

Prevention:

- prove manager existence and child parentage together;
- revalidate immediately before mutation;
- never infer healthy ownership from `sv status` alone;
- avoid duplicate-manager churn;
- accept new PIDs when the service topology is correct.

## E-009 — Crond split-brain and transient child absence

Status: repaired; automatic recovery verified.

Historical split-brain:

- manager-owned `runsv crond` had no valid supervised daemon PID;
- detached old `crond -n -s` remained under PID 1.

Verified V2 repair:

- file-gated approval accepted;
- old detached crond exited;
- first supervised start timed out;
- automatic availability recovery restored one supervised crond.

2026-07-22 transient:

- one snapshot found a manager-owned crond runsv but no live child, producing `6/7`;
- targeted follow-up found live crond PID `13521`, PPID `24619`, command `crond -n -s`;
- crond and crond/log both reported `run`;
- no manual restart was required.

Prevention:

- accept documented `crond -n -s` foreground form;
- verify manager, runsv, wrapper, service PID, and daemon parentage;
- when ownership is correct but a child is absent, allow one short bounded recovery resample before mutation;
- preserve automatic recovery;
- do not rerun V5 for a crond-only transient.

## E-010 — RapidAPI calendar fallback always enabled

Status: runtime-contained; source fix deferred.

Root cause:

- watcher source says calendar guard is disabled;
- condition remains true whenever `calendar_guard.py` exists because of a second `|| [[ -f ... ]]` clause;
- the guard falls back to RapidAPI whenever TradingEconomics returns no events;
- watcher processes multiple pairs on each cycle;
- a non-empty runtime key enabled real fallback calls.

Evidence:

- recent EURUSD and GBPUSD `safe via rapidapi` log lines;
- provider email reporting 100% BASIC quota usage;
- `.env.runtime` now contains exactly one empty runtime key declaration.

Prevention:

- explicit enable flag;
- remove the always-true fallback clause;
- cache calendar results across pairs/cycles;
- enforce a daily call budget;
- surface quota/429 errors;
- keep emergency runtime disable reversible.

## E-011 — Ship-time stale-reason suppression mismatch

Status: OPEN and deferred.

Verified mismatch:

- emitted reasons use `watcher_stale`, `updater_stale`, and `shadow_stale`;
- suppression regex expects `watcher_log_stale`, `updater_log_stale`, and similar names.

Effect:

- intended ship-mode suppression is ineffective;
- Telegram can emit misleading DEGRADED transitions.

Prevention:

- normalize reason identifiers;
- test suppression against actual emitted values;
- base same-boot freshness on monotonic useful progress.

## E-012 — Operational command/package failures

Status: process correction active.

Observed mistakes:

- broad audits produced archive noise;
- recursive scans risked runit FIFOs;
- `pipefail` converted valid zero-match checks into silent exits;
- top-level `exit` closed the Termux session;
- interactive approval loops failed or were killed;
- repeated giant scripts wasted time and tokens;
- a wrapper assumed a missing approval meant no repair, but persistent logs later proved execution had occurred;
- read-only blocks were sometimes much larger than the narrow failing scope required.

Prevention:

- display runtime error log first;
- active paths only;
- safe zero-match counts;
- subshell guards or controlled return;
- file-gated approvals;
- persistent execution logs;
- compact packages;
- one next action;
- inspect evidence before repeating repair.

## E-013 — Fixed-PID endurance criterion

Status: corrected.

Failure:

- Phase 4 was temporarily judged by whether exact manager, runsv, and wrapper PIDs survived for 12 hours;
- healthy automatic reconstruction under new PIDs was therefore classified as failure.

Why this was wrong:

- runit is designed to restart children;
- Android may replace the manager during the same boot;
- PID identity is an implementation detail, not the reliability outcome.

Prevention:

- judge one-manager ownership, seven supervisor/wrapper chains, zero orphans, one supervised crond, API protection, and useful progress;
- record PID changes as restart events;
- escalate only when recovery is incomplete, duplicated, orphaned, or persistently unavailable.

## E-014 — `/proc/uptime` permission failure

Status: corrected.

Failure:

A final read-only audit attempted to read `/proc/uptime` and stopped with:

`PermissionError: [Errno 13] Permission denied: '/proc/uptime'`

Prevention:

- never depend on `/proc/uptime` on this Android build;
- use `time.monotonic()` for package-relative timing;
- read `/proc/<pid>/stat` only when process metadata is necessary and readable;
- avoid process-age gates when functional state is sufficient.

## E-015 — Current-date/time interpretation error

Status: corrected.

Failure:

- the user stated the audit was being run on July 21 after more than 12 hours;
- the workflow incorrectly treated it as a fresh 22-minute sample and instructed another wait.

Prevention:

- reconcile explicit user date/time with the date of the prior baseline;
- do not infer “today” from a stale conversation checkpoint;
- prefer direct runtime evidence over conversational elapsed-time arithmetic.

## E-016 — Transient failure escalated before recovery grace

Status: corrected.

Failure:

- one snapshot captured crond without a child and immediately classified Phase 4 as failed;
- the next targeted audit proved runit had automatically recovered crond.

Prevention:

- when manager ownership remains correct and only one child is missing, take one compact targeted recovery sample before proposing mutation;
- do not rerun the seven-service handoff for a single-service transient;
- distinguish `RECOVERING`, `PERSISTENTLY_DOWN`, and `STRUCTURALLY_BROKEN`.

## E-017 — Documentation lag after material runtime changes

Status: corrected for the 2026-07-22 checkpoint.

Failure:

- continuity and AI handoff still named manager PID `4090` and Phase 4 as pending after later manager recovery and final closure evidence.

Prevention:

- update GitHub issue, detailed incident record, `CONTINUITY_CURRENT.md`, `ERRORS.md`, and `AI_START_HERE.md` immediately after a phase gate or material correction;
- current-state files must describe invariants and latest evidence, not obsolete PIDs as permanent truth.

## Efficient diagnostic order when signals stop

Do not first blame H1 veto, thresholds, ADX, strategy, or pair selection.

### Gate A — functional snapshot

1. one standard manager;
2. seven manager-owned supervisors;
3. seven running wrapper chains;
4. zero orphaned supervisors;
5. one supervised crond;
6. RapidAPI protection;
7. useful-progress markers.

If Gate A passes, stop infrastructure diagnosis.

### Gate B — targeted diagnostic

Inspect only the failed service or data path:

- watcher/updater/closer/shadow progress;
- crond and canonical crontab;
- provider quota/cache freshness;
- ACTIVE signal lifecycle;
- Telegram/Supabase connectivity;
- health-transition truth.

### Gate C — recovery sample

When ownership is correct but one child is absent, allow one bounded recovery sample. Do not mutate unless the failure persists.

### Gate D — mutation

Require persistent failure, narrow cause/hypothesis, backup, rollback, separate typed approval, and independent verification.
