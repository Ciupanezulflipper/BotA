# BotA Errors and Silent-Failure Register

Last updated: 2026-07-20

Purpose: record runtime failures and prevention rules that must not be rediscovered from scratch.

Detailed current evidence: `docs/RUNTIME_CHECKPOINT_2026-07-20.md`.

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

Status: restored previously; current canonical hash mismatch requires later reconciliation.

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

Status: improved, but runtime truth remains imperfect.

Current issue:

- Daily Proof reports more runtime evidence than before;
- however, Telegram and supervisor health still depend partly on wall-clock/file-mtime freshness;
- a quiet successful cycle can be classified stale;
- restart log touches can look like recovery.

Prevention:

- use monotonic useful-progress markers;
- separate service presence from useful progress;
- never treat one RECOVERY notification as proof of structural health.

## E-004 — Termux/Android runtime fragility

Status: active Phase 4 blocker.

Known risks:

- Android can kill the standard `runsvdir` manager while child `runsv` supervisors remain under PID 1;
- reboot and app lifecycle can produce mixed manager/orphan ownership;
- mobile network and ship environment can interrupt providers and Telegram.

Current evidence:

- reboot recovery gate passed;
- later endurance evidence showed manager loss and orphaned supervisors.

Prevention:

- verify exactly one standard manager;
- verify every runsv parent immediately before mutation;
- use wake lock and Termux:Boot;
- run bounded post-reboot/endurance parentage checks.

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
- server clock source unavailable.

Current evidence:

- Twelve Data warning: 600/800 credits;
- Global Economic Calendar API BASIC quota: 100% consumed.

Prevention:

- per-provider call budgets;
- explicit quota/429 logging;
- cache reuse;
- failover with bounded retries;
- do not conflate separate provider quotas.

## E-007 — ProfitLab observability gap

Status: partially closed.

- BotA runtime health is pushed to Supabase.
- ProfitLab must continue distinguishing quiet/no-signal from dead/offline runtime.
- Health truth still depends on fixing local false stale/recovery classification.

## E-008 — Dead standard runsvdir with orphaned supervisors

Status: OPEN and current structural blocker.

Verified current state:

- latest forensic snapshot: `STANDARD_MANAGER_COUNT=0`;
- all six BotA runsv supervisors are under PID 1;
- runsv crond is also under PID 1;
- one live supervised crond remains available.

Prevention:

- prove manager existence and child parentage together;
- revalidate immediately before any daemon/supervisor migration;
- never infer healthy ownership from `sv status` alone;
- avoid duplicate-manager churn.

Required recovery:

- restore exactly one standard Termux `runsvdir`;
- migrate seven stable runsv supervisors beneath it;
- prove stable parentage across bounded samples;
- avoid historical replay and duplicate wrappers.

## E-009 — Crond split-brain and invalid supervise PID

Status: repaired for the current boot; do not rerun blindly.

Verified prior state:

- manager-owned `runsv crond` had no valid supervised daemon PID;
- detached old `crond -n -s` remained under PID 1.

Verified repair:

- file-gated approval accepted;
- old crond exited;
- first supervised start timed out;
- automatic availability recovery succeeded with crond PID 28296.

Prevention:

- accept documented `crond -n -s` foreground form;
- validate manager, runsv, service PID, and old daemon immediately before mutation;
- preserve automatic availability recovery;
- inspect persistent logs before assuming an approval file merely disappeared.

## E-010 — RapidAPI calendar fallback always enabled

Status: OPEN; runtime-only mitigation staged.

Root cause:

- watcher source says calendar guard is disabled;
- condition remains true whenever `calendar_guard.py` exists because of a second `|| [[ -f ... ]]` clause;
- the guard falls back to RapidAPI whenever TradingEconomics returns no events;
- watcher runs every 900 seconds and processes multiple pairs;
- non-empty runtime key enables real fallback calls.

Evidence:

- recent EURUSD and GBPUSD `safe via rapidapi` log lines;
- provider email reporting 100% BASIC quota usage.

Prevention:

- explicit enable flag;
- remove always-true fallback clause;
- cache calendar results across pairs/cycles;
- enforce daily call budget;
- surface 429/quota errors;
- keep runtime emergency disable reversible.

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
- a wrapper assumed a missing approval meant no repair, but persistent logs later proved the repair had executed.

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

## Diagnostic order when signals stop

Do not first blame H1 veto, thresholds, ADX, strategy, or pair selection.

Check in this order:

1. standard manager count and runsv parentage;
2. crond and canonical crontab integrity;
3. watcher/updater/closer/shadow useful progress;
4. provider quotas and cache freshness;
5. ACTIVE signal lifecycle state;
6. Telegram/Supabase/provider connectivity;
7. health-transition truth.
