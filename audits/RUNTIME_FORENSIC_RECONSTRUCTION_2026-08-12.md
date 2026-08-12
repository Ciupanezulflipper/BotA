# BotA Runtime Forensic Reconstruction — 2026-08-12

**Repository:** `Ciupanezulflipper/BotA`  
**Record date:** 2026-08-12  
**Purpose:** Canonical checkpoint after a full adversarial reconstruction of BotA runtime, observability, deployment provenance, live-market evidence, historical audits, GEMS, PR history, and strategy evidence.

> This file is a forensic record. It does **not** authorize a production runtime mutation, strategy change, threshold change, Android cutover, old R6 execution, or replacement-runtime implementation by itself.

---

## 1. Executive conclusion

The prior simplified conclusion — that the phone lost its source of truth and that runit / multiple control authorities were proven to be the primary root cause — does **not** survive the full review.

The evidence supports the following decomposition:

```text
TRADING_SCORING_ENGINE=FUNCTIONAL
MARKET_DATA_PATH=FUNCTIONAL_WHEN_CYCLE_EXECUTES
TELEGRAM_DELIVERY=PROVEN
SUPABASE_PUBLICATION=PROVEN
ANDROID_PROCESS_LIFECYCLE=INTERMITTENTLY_UNSTABLE
INITIATING_MANAGER_LOSS_CAUSE=NOT_PROVEN
PR89_WATCHDOG_FAULT_TEST=VALID_PASS_FOR_TESTED_FAULT
OBSERVABILITY_FALSE_GREEN_BUG=PROVEN
OBSERVABILITY_LOG_ROUTING_DEFECT=PROVEN
ALERTS_CSV_IS_EVALUATION_JOURNAL=YES
DUPLICATE_ALERT_ROWS_ARE_NOT_BY_THEMSELVES_DUPLICATE_TRADES=YES
STRATEGY_EDGE=UNPROVEN
STRATEGY_HOPELESS=NOT_PROVEN
RUNTIME_FAILURE_EXPLAINS_BAD_HISTORICAL_STRATEGY_RESULTS=NO
MORE_UNBIASED_MARKET_EVIDENCE_REQUIRED=YES
```

The most defensible current statement is:

> BotA's trading/data/delivery engine has real production proofs. The unresolved production problem is a recurring Android/Termux lifecycle fault broader than the fault PR #89 injected, plus genuine useful-progress stalls. Separately, the live readiness/ledger layer contains at least two proven semantic/wiring defects that can misreport healthy/rejected/delivery state. These three problem classes were repeatedly conflated.

---

## 2. Corrections to prior conclusions

### 2.1 Phone Git HEAD mismatch is not proof of provenance failure

The phone local HEAD:

`4339543551aae2e2bcbf727aefe96e3eb103b665`

was explicitly documented in Issue #9 together with the rule that the phone checkout is intentionally dirty and is **not** the deployment identity.

The deployment identity was defined by:
- hash-pinned reviewed runtime files,
- exact phone parity checks,
- independent phone acceptance evidence,
- explicitly recorded runtime source baselines.

Therefore:

```text
PHONE_HEAD_NOT_EQUAL_MAIN != PROVEN_SOURCE_OF_TRUTH_FAILURE
```

Do not infer uncontrolled production merely because the phone worktree HEAD differs from current GitHub `main`.

### 2.2 Telegram DEGRADED -> RECOVERY intervals are not direct outage duration

`bota-supervisor` runs on a default 300-second interval.

The native watchdog/recovery loop is substantially more frequent.

Therefore a DEGRADED alert observed at one supervisor sample and a RECOVERY alert at the next supervisor sample may represent an underlying topology repair that happened much earlier than the Telegram recovery timestamp.

Do not sum Telegram DEGRADED-to-RECOVERY alert intervals and call that number "downtime."

Actual useful-work staleness evidence is stronger, e.g.:
- updater stale ~7543 s (~125.7 min),
- updater stale ~3330 s (~55.5 min),
- updater stale ~2138 s (~35.6 min),
- DEADMAN monotonic shadow age ~125 min.

Those are real stale-progress windows.

### 2.3 DEADMAN wall-clock display and monotonic age are different clock domains

Package #1 intentionally separated:
- trusted/server epoch for trading/event/session semantics,
- monotonic / `CLOCK_BOOTTIME` for elapsed-time and stale-progress semantics.

The displayed shadow timestamp is not required to numerically match monotonic age.

Therefore the previously suspected "125 min arithmetic contradiction" was not a valid defect by itself.

### 2.4 Repeated rows in `alerts.csv` are not automatically duplicate trades

The July observability fix deliberately journals every completed evaluated decision before rejection/delivery gates.

Delivery dedup state is only updated after confirmed successful Telegram delivery.

Therefore repeated same-direction rows across consecutive cycles can be valid repeated evaluations.

Treat:

```text
alerts.csv = evaluation journal
```

not:

```text
alerts.csv = unique delivered-trade ledger
```

Unique delivered trades require delivery evidence / delivery hash / authoritative trade outcome identity.

---

## 3. What is proven functional

### 3.1 Real production trading path has worked

At least two real delivered examples are established.

Historical example:
- USDJPY M15 BUY
- score ~81.60
- entry ~159.16400
- SL ~159.01418
- TP ~159.46365

Current 2026-08-12 example:
- GBPUSD M15 BUY
- score ~84.90
- entry ~1.35379
- SL ~1.35222
- TP ~1.35692

The 2026-08-12 evidence included:
- decision persisted in `alerts.csv`,
- Telegram delivery,
- Telegram chart delivery,
- Supabase publication:
  `published GBPUSD BUY entry=1.35379`.

This proves the live path can execute end to end.

It does **not** prove strategy profitability or continuous runtime availability.

### 3.2 R4/R5 still matter

R4 proved deterministic BotA replay semantics and byte parity after harness defects were fixed.

R5 proved bounded real-engine subprocess timeout / kill / recovery behavior in the disposable test boundary.

These do not prove Android lifecycle robustness, but they are valid component evidence.

---

## 4. PR #89 was a legitimate PASS for the fault it actually tested

PR #89:
- title: `fix: persist native watchdog with fail-closed cron guardian`
- merged commit: `741a2756675a789dc23ab7d6df3b2675bc474fd6`
- PR head: `e4eb7a87f5b9930b05e161bf7baef1da6268bb36`

The controlled phone fault injection on 2026-08-09:
1. revalidated exact PR #89 runtime parity,
2. revalidated one manager / owned 7/7 / running 7/7 / zero orphans / zero duplicates,
3. revalidated one watchdog PID and active FLOCK holder,
4. sent SIGTERM **only** to the watchdog,
5. observed old watchdog exit,
6. observed the cron guardian naturally recreate a replacement watchdog,
7. observed replacement watchdog acquire the lock,
8. observed final healthy topology.

Recorded result included:

```text
OLD_WATCHDOG_PID=25085
NEW_WATCHDOG_PID=32337
OLD_WATCHDOG_EXIT=PASS
GUARDIAN_CRON_RECOVERY_EVENT=PASS
FINAL_CONTROL_PLANE=MANAGERS=1 OWNED=7/7 RUNNING=7/7 ORPHANED=0 DUPLICATES=0
FINAL_WATCHDOG_PIDS=[32337]
FINAL_WATCHDOG_LOCK_HOLDERS=[32337]
PR89_FILES_UNCHANGED=PASS
CRONTAB_UNCHANGED=PASS
SINGLE_MANAGER_AUTHORITY_UNCHANGED=PASS
PR89_WATCHDOG_FAULT_INJECTION=PASS
ROLLBACK_EXECUTED=NO
```

Therefore:

```text
PR89_PASS_WAS_FAKE=NO
PR89_TEST_COVERED_WATCHDOG_DEATH=YES
PR89_TEST_PROVED_MANAGER_LOSS_RECOVERY=NO
PR89_TEST_PROVED_CORRELATED_MANAGER_PLUS_CROND_LOSS=NO
```

The later production failures were broader than the injected fault.

This is a **fault-coverage gap**, not evidence that PR #89 never worked.

---

## 5. Proven observability defect #1 — false-green rejection semantics

### 5.1 Historical live CSV schema drift

The retained phone `alerts.csv` has historical schema drift:
- older header uses the field `rejected`,
- newer rows contain the extended payload / newer field set.

The August 7 funnel forensics already documented a legacy 13-column header with newer wider rows.

### 5.2 Deployed watcher reconciler reads the wrong rejection field

The deployed baseline `tools/watcher_cycle_ledger.py` does:

```python
rejected = truthy(row.get("filter_rejected"))
```

But the legacy header exposes:

```text
rejected
```

not:

```text
filter_rejected
```

When the appended row represents a real HOLD / rejected decision but the parsed dictionary lacks `filter_rejected`, the reconciler defaults rejection to false.

A real rejection can therefore become:

```text
filter_rejected=false
decision_persisted_no_delivery_evidence
```

and can later be summarized as:

```text
EVALUATED_ACCEPTED
```

even though the source evaluation was rejected.

### 5.3 Classification

```text
OBSERVABILITY_FALSE_GREEN_SEMANTIC_BUG=PROVEN
ROOT=LEGACY_HEADER_FIELD_MISMATCH
TRADING_ENGINE_FAILURE=NO
DELIVERY_FAILURE_IMPLIED=NO
```

This defect existed in the deployed baseline before Monday.

---

## 6. Proven observability defect #2 — current-cycle log evidence routed away from the reconciler

### 6.1 Gated wrapper uses a temporary current-cycle stderr path

The gated watcher path captures current watcher stderr in a temporary / per-cycle file boundary.

### 6.2 `watcher_cycle_ledger.py` still inspects historical `logs/cron.signals.log`

The reconciler separately loads:

```text
logs/cron.signals.log
```

for current-cycle filter / Telegram / Supabase evidence.

Phone evidence shows that `cron.signals.log` stopped advancing on 2026-08-08.

Therefore it is possible for:
- current watcher execution to happen,
- a current decision row to be appended,
- Telegram and Supabase to succeed,
- while the reconciler consults stale `cron.signals.log` and finds no matching delivery evidence.

This naturally produces:

```text
decision_persisted_no_delivery_evidence
```

even when delivery actually succeeded.

### 6.3 Classification

```text
OBSERVABILITY_LOG_ROUTING_DEFECT=PROVEN
CURRENT_CYCLE_STDERR_SOURCE_AND_RECONCILER_SOURCE=NOT_THE_SAME
TRADING_ENGINE_FAILURE=NO
```

This defect combines with the legacy rejection-field mismatch and makes the compact progress ledger less trustworthy than the raw evaluation + delivery evidence.

---

## 7. Why the Monday-readiness harness missed these two observability defects

`tools/monday_readiness_check.py` explicitly:
- creates an isolated temporary `BOTA_ROOT`,
- stages a minimal clean tool set,
- uses `WATCHER_GATED_DRY_RUN`,
- does not execute the full live inner watcher,
- does not send Telegram,
- does not write Supabase,
- does not reproduce the phone's months-old accumulated CSV state.

Therefore the harness did not exercise:
- legacy 13-column header + newer appended rows,
- actual accumulated phone files,
- live watcher stderr routing,
- real Telegram delivery,
- real Supabase publication,
- Android lifecycle behavior.

The engineering record also correctly retained:

```text
MONDAY_READY=NO
```

after PR #89 fault injection, because genuine natural open-market same-cycle proof still remained.

Therefore:

```text
READINESS_HARNESS_FALSELY_CERTIFIED_FULL_PRODUCTION_READY=NO
READINESS_HARNESS_HAD_REAL_STATE_COVERAGE_GAPS=YES
```

---

## 8. Android / Termux control-plane failure — real but initiating cause remains unproven

Observed historical and current pattern:

```text
HEALTHY
-> runsvdir manager absent / lost
-> individual runsv children survive and reparent to PID 1
-> ownership becomes partial/orphaned
-> watchdog/recovery restores manager ownership
-> later degradation recurs
```

Historical examples included:
- owned 6/7 + orphan 1,
- owned 1/7 + orphan 6,
- one manager with all seven service supervisors orphaned,
- later healthy 7/7 states.

The exact initiating reason the manager disappears is still:

```text
INSUFFICIENT_EVIDENCE
```

Possible classes include:
- Android/Termux process lifecycle termination,
- resource / phantom-process pressure,
- internal service-daemon/runsvdir exit,
- race / lifecycle interaction,
- other process-control event.

Do **not** report any one of those as proven root cause until direct death provenance exists.

### Important downgrade of an earlier claim

Historically, overlapping authorities were absolutely real:
- custom runsvdir startup,
- multiple Termux:Boot daemon starters,
- detached crond paths,
- watchdogs / recovery tools,
- runit supervision.

They amplified ownership ambiguity and required repair.

However, after consolidation and PR #89, it is too strong to say:

```text
MULTIPLE_CURRENT_AUTHORITIES_PROVEN_PRIMARY_ROOT_CAUSE=YES
```

The supported statement is:

```text
MULTIPLE_AUTHORITIES_HISTORICALLY_AMPLIFIED_FAILURES=YES
PRIMARY_INITIATING_MANAGER_LOSS_CAUSE=NOT_PROVEN
```

---

## 9. Useful-progress stalls are real and separate from false-green semantics

Not every DEGRADED notification is equivalent to business-path downtime.

However, independently observed monotonic useful-progress ages prove real stalls.

Examples:
- ~7543 s,
- ~3330 s,
- ~2138 s,
- shadow DEADMAN ~125 min.

Later evidence also showed recovery:
- updater `fetch_success=12`,
- updater `fetch_fail=0`,
- updater `build_fail=0`,
- shadow returned to `completed`,
- OANDA fetches succeeded across expected pairs/timeframes.

Therefore:

```text
PIPELINE_PERMANENTLY_DEAD=NO
USEFUL_PROGRESS_INTERRUPTION=YES
DATA_PROVIDER_PERMANENTLY_DEAD=NO
```

The exact cause of each long useful-progress stall still requires direct attribution.

---

## 10. GEMS findings that should be reused rather than reinvented

The full GEMS review remains relevant to future runtime work.

### GEM 23 — `lib_utils.py`
Retained high-value patterns:
- atomic JSON writes,
- file lock,
- FX-hours helper,
- dedup hash.

### GEM 52 — `tg_control.py`
Retained pattern:
- single-instance lock,
- stale-heartbeat alert.

Useful as a pattern only; do not copy unrelated Telegram/control behavior blindly.

### GEM 71 — `provider_limits.py`
Retained pattern:
- provider rate-limit registry,
- JSON persistence,
- atomic write.

### Core retained trading/runtime components
GEMS also marks major existing components as high value, including:
- `data_fetch_candles.sh`,
- `indicators_updater.sh`,
- `market_open.sh`,
- `signal_watcher_pro.sh`,
- `scoring_engine.sh`,
- `m15_h1_fusion.sh`,
- signal/outcome supporting tools.

The correct lesson is **reuse proven primitives and preserve trading-engine behavior**, not add another framework or rewrite everything because the control plane is unstable.

---

## 11. Strategy evidence — runtime reliability must not be used as an excuse for poor historical results

Historical delivered BotA M15 evidence since 2026-06-01:
- 13 delivered signals,
- 3 wins,
- 9 losses,
- 1 cancelled,
- -71.4 pips.

March local outcome dataset:
- 51 rows,
- 13 wins,
- 38 losses,
- -264.1 pips in the joined component audit.

Notable component findings:
- score 85+: poor in the March sample,
- extreme RSI: poor,
- ADX 30-39: poor,
- ADX 20-29: substantially better in-sample.

March counterfactual:
- ADX < 30: 17 trades, 9W/8L, +98.0 pips,
- score >=70 + ADX <30: 12 trades, 9W/3L, +174.2 pips,
- score >=70 + ADX <30 + no extreme RSI: 7/7, +171.0 pips,
- but the 7/7 subset is explicitly high-overfit risk.

Later June-July matched cross-check:
- published outcomes: 13,
- local component match: 9,
- matched baseline: 2W/7L, -70.2 pips,
- score >=70 + ADX <30: 2W/3L, +13.1 pips,
- score >=70 + ADX <30 + no extreme RSI: 2W/2L, +28.9 pips,
- ADX >=30: 0W/4L, -83.3 pips.

Coverage remained incomplete.

### Bayesian / Monte Carlo reconstruction

Using a neutral Beta(1,1) prior:

For 3W/9L resolved recent trades:
- posterior mean win rate ~28.6%,
- approximate 95% interval ~9.1% to 53.8%,
- probability true win rate >33.3% idealized 2R/-1R break-even ~32.2%,
- posterior-predictive probability next 100 resolved trades finish positive under idealized +2R/-1R payoff ~32.6%.

For March 13W/38L:
- posterior mean ~26.4%,
- approximate 95% interval ~15.6% to 38.9%,
- probability true win rate >33.3% ~12.9%.

For later 2W/3L `score>=70 + ADX<30` subset:
- posterior mean ~42.9%,
- approximate 95% interval ~11.8% to 77.7%.

Interpretation:
- current strategy edge is not proven,
- current strategy is not proven hopeless,
- the ADX<30 direction remains plausible but severely underpowered,
- no production policy/threshold change is authorized from these samples,
- runtime instability cannot be used to erase the negative historical outcome evidence.

---

## 12. Correct causal hierarchy

### Proven
1. Trading engine can produce real signals.
2. Market data acquisition can succeed.
3. Telegram delivery can succeed.
4. Supabase publication can succeed.
5. PR #89 watchdog resurrection can work exactly as tested.
6. Manager/orphan topology degradation recurs in real Android operation.
7. Useful-progress stalls occur.
8. Legacy `alerts.csv` schema and reconciler field expectations are incompatible.
9. Reconciler current-cycle log evidence can come from a stale/non-current log path.
10. Compact watcher ledger can therefore produce false-green / missing-delivery semantics.
11. Historical strategy results are weak and profitability is unproven.

### Plausible but not proven
1. Android lifecycle/resource pressure kills the manager.
2. An internal runit/service-daemon failure kills the manager.
3. One specific lifecycle mechanism explains every observed stale-progress interval.
4. Replacing runit will automatically cure all Android lifecycle failures.
5. Moving to cloud would automatically fix strategy quality.

### Disproven / withdrawn as conclusions
1. `phone HEAD != GitHub main` proves uncontrolled source-of-truth drift.
2. Summed Telegram DEGRADED intervals equal actual runtime outage.
3. DEADMAN 125-minute age is invalid because wall-clock display differs.
4. Repeated `alerts.csv` rows automatically mean duplicate trades.
5. PR #89's PASS was meaningless.
6. Multiple current authorities are proven to be the initiating root cause of today's manager loss.
7. The trading engine itself is the main reason useful evidence is missing.

---

## 13. Implication for replacement-runtime architecture

A smaller owner/runtime architecture remains defensible.

But its justification must be stated correctly.

Do **not** say:

> Replace runit because runit/multiple authorities are proven to be the root cause.

Instead say:

> Reduce persistent topology and lifecycle surface as a risk-reduction measure under an unresolved hostile Android lifecycle, while preserving the trading engine and proving the replacement empirically against the existing runtime.

The replacement must still:
- have one lifecycle owner,
- derive health from useful work,
- use bounded I/O/subprocess deadlines,
- reconcile durable state before useful work,
- prove prior generation descendants are gone before replacement useful work,
- fail closed on identity/state ambiguity,
- keep trading clock separate from elapsed supervision clock,
- avoid strategy changes,
- beat the legacy runtime in isolated Android shadow evidence before cutover.

The exact initiating manager-death mechanism should still be captured if feasible, but lack of provenance must not be replaced by an invented cause.

---

## 14. Why six months of work did not converge cleanly at the final boundary

The evidence does **not** support "nothing useful was accomplished."

The project discovered and fixed real issues:
- Yahoo 429 retry storm,
- market-phase contract mismatch,
- stale watcher lock,
- pre-journal dedup observability loss,
- delivery-hash ordering,
- trusted clock propagation,
- stale crond singleton ownership,
- PID-1 orphaned `runsv` topology,
- runtime dependency contract,
- watchdog singleton / FLOCK behavior,
- watchdog resurrection via guardian,
- deterministic replay,
- real-engine timeout/recovery semantics.

The larger process failure was methodological:

> Too much effort went into recovery and clean synthetic qualification before the final accumulated-phone-state / natural-market boundary was fully exercised.

Clean CI and isolated harnesses did not reproduce:
- old CSV header state,
- months of append history,
- log-routing drift,
- real Android process death,
- real Telegram/Supabase side effects,
- real provider/network timing.

This is why static reviews and clean harnesses could pass while production still exposed new behavior.

Future acceptance must include dirty/accumulated-state fixtures and live Android lifecycle evidence, not only clean ephemeral roots.

---

## 15. Required future reading order

For future BotA runtime/reliability sessions, read this file before re-running broad forensics.

Recommended order:

1. `audits/RUNTIME_FORENSIC_RECONSTRUCTION_2026-08-12.md` — this record.
2. `README.md` — architecture direction, but do not treat root-cause language as stronger than this forensic record.
3. `GEMS.md` — retained implementation/reliability patterns.
4. Issue #9 — production readiness and phone evidence history.
5. PR #89 and its 2026-08-09 phone fault-injection record.
6. `RESOLVED.md` — proven historical fixes.
7. `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`.
8. March outcome / ADX-RSI counterfactual / June-July temporal cross-check audits.
9. R1-R5 evidence and blocked old R6 review when working on replacement-runtime qualification.

Do not start by replaying the entire repository history unless new evidence directly contradicts this checkpoint.

---

## 16. Current state machine after this reconstruction

```text
FORENSIC_RECONSTRUCTION_2026_08_12=COMPLETE
PREVIOUS_OVERSIMPLIFIED_ROOT_CAUSE=RETRACTED
PHONE_DEPLOYMENT_PROVENANCE_MODEL=CONTROLLED_HASH_PINNED
TRADING_ENGINE_FUNCTIONAL=YES
LIVE_SIGNAL_PATH_PROVEN=YES
PR89_FAULT_INJECTION_VALID=YES
PR89_FAULT_COVERAGE_COMPLETE_FOR_ALL_LIFECYCLE_FAILURES=NO
ANDROID_MANAGER_LOSS_RECURS=YES
ANDROID_MANAGER_LOSS_INITIATOR=NOT_PROVEN
USEFUL_PROGRESS_STALLS=PROVEN
FALSE_GREEN_LEDGER_SEMANTICS=PROVEN
CURRENT_CYCLE_LOG_ROUTING_DEFECT=PROVEN
ALERTS_CSV_DUPLICATE_ROWS_EQUAL_DUPLICATE_TRADES=NO
STRATEGY_EDGE=UNPROVEN
STRATEGY_THRESHOLDS_FROZEN=YES
OLD_R6=BLOCKED_DO_NOT_EXECUTE
REPLACEMENT_RUNTIME_IMPLEMENTATION_AUTHORIZED_BY_THIS_FILE=NO
ANDROID_PRODUCTION_MUTATION_AUTHORIZED_BY_THIS_FILE=NO
```

---

## 17. Minimum next engineering actions

This record does not execute them, but the smallest evidence-driven sequence is:

1. Repair the watcher observability contract:
   - schema-aware parsing of historical `alerts.csv`,
   - normalize `rejected` and `filter_rejected`,
   - use the actual current-cycle stderr/event source,
   - add regression fixtures reproducing the real historical header drift,
   - prove a rejected HOLD cannot become `EVALUATED_ACCEPTED`.

2. Add direct manager-death provenance instrumentation if it can be done without destabilizing production:
   - exact process identity,
   - exit/termination classification where observable,
   - boot ID,
   - timestamps in monotonic + trusted wall clock,
   - surrounding Android/runtime state.

3. Continue replacement-owner design/qualification separately.
   - Do not claim its need is based on a proven runit root cause.
   - Prove it is more resilient on Android.

4. Resume unbiased real-market evidence collection only when observability can distinguish:
   - evaluated reject,
   - evaluated accept,
   - delivery attempted,
   - delivered,
   - published,
   - stale/no-cycle,
   - genuine runtime interruption.

5. Do not modify strategy thresholds from the small ADX/RSI subsets.
   - Preserve them as hypotheses for later out-of-sample validation.

---

## 18. Explicitly not authorized by this record

```text
NO_STRATEGY_THRESHOLD_CHANGE
NO_ADX_POLICY_PRODUCTION_CHANGE
NO_RSI_POLICY_PRODUCTION_CHANGE
NO_PAIR_SCOPE_CHANGE
NO_TIMEFRAME_SCOPE_CHANGE
NO_OLD_R6_EXECUTION
NO_ANDROID_CUTOVER
NO_RUNIT_REMOVAL
NO_CLOUD_MIGRATION
NO_PROFITABILITY_CLAIM
NO_ROOT_CAUSE_CLAIM_WITHOUT_DEATH_PROVENANCE
```

---

## 19. Primary source map

### GitHub runtime / provenance
- Issue #9 — `BotA production readiness — current source of truth and reliability record`
- phone local HEAD documented as `4339543551aae2e2bcbf727aefe96e3eb103b665`
- phone runtime source baseline documented as `5cbfbf11fd98d9a40b1d5ea28995f584ec9da080`
- PR #89 merge: `741a2756675a789dc23ab7d6df3b2675bc474fd6`
- PR #89 head: `e4eb7a87f5b9930b05e161bf7baef1da6268bb36`
- Issue #9 comment `5233692332` — PR #89 watchdog fault injection PASS
- current main at reconstruction start: `d563695ddcd8943d2a140dac8a26d34b929d48d5`

### Key files inspected
- `GEMS.md`
- `RESOLVED.md`
- `tools/watcher_cycle_ledger.py`
- `tools/watcher_gated_cycle.sh`
- `tools/run_signal_watcher_with_ledger.sh`
- `tools/monday_readiness_check.py`
- `tools/native_watchdog_guard.py`
- `tools/native_service_daemon_watchdog.py`
- `tools/bota_supervisor.sh`
- `services/bota-supervisor/run`
- `services/bota-shadow/run`
- `tools/run_shadow_manager.sh`
- `tools/runtime_dependency_check.py`
- `tools/pipeline_health.py`
- `tools/heartbeat_runtime.py`
- `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`

### Strategy/history evidence
- PR #50 — cooldown semantics and recent signal quality
- PR #51 — local signal ledger inventory
- PR #52 — March score-component outcome calibration
- PR #53 — ADX/RSI counterfactual
- PR #54 — June-July temporal cross-check

### Replacement-runtime qualification context
- R1-R5: component/prototype qualification PASS within their stated boundaries
- old R6 branch: `test/r6-runtime-gate-20260811`
- old R6 commit: `6fda9212bb4addcf5314a1e31c4919ac9d553101`
- old R6 remains BLOCKED / DO NOT EXECUTE

---

## 20. Human-readable bottom line

BotA has a real trading engine and a real delivery path. It also has a real Android lifecycle reliability problem. The current evidence does not prove what kills the runsvdir manager, and it does not justify calling runit or multiple authorities the initiating root cause. PR #89 genuinely proved watchdog resurrection, but production later exhibited a broader correlated failure class than the injected test.

At the same time, the readiness/ledger layer is not merely noisy: two concrete implementation defects can misclassify rejected decisions and lose current-cycle delivery semantics. Those defects materially distorted our interpretation of production health.

The correct next phase is therefore not "throw everything away" and not "pretend production was fine." It is:
1. repair observability truth,
2. instrument the unresolved lifecycle boundary,
3. qualify the smaller owner/runtime as a risk-reduction architecture,
4. collect clean, unbiased market evidence,
5. judge the trading strategy separately from infrastructure reliability.

This file should be treated as the canonical 2026-08-12 forensic checkpoint unless later direct evidence explicitly supersedes one of its findings.
