# BotA Operational Runtime and Delivery Forensics — 2026-09-03

## Scope

This is a docs-only post-closure forensic record. It preserves Android/Termux runtime, deployment, watcher, Telegram and Supabase evidence gathered after the final BotA strategy closure.

It does **not** reopen BotA strategy validation, authorize tuning, authorize Hetzner Production deployment, or alter the final corpus-gate decision.

```text
FINAL_STRATEGY_VERDICT=CLOSE
ACTIVE_STRATEGY_VALIDATION=NO
STRATEGY_TUNING_AUTHORIZED=NO
PRODUCTION_READY=NO
HETZNER_PRODUCTION_CUTOVER=NO
OPERATIONAL_FORENSICS_ONLY=YES
```

Canonical main before this evidence record:

```text
cecd28c40d21d520c932acd3e8bb60cc5edeaf76
```

## Executive forensic verdict

Two independent runtime-dependency closure failures are now evidenced in the Aug-16 Package-6 phone deployment.

1. `tools/run_signal_watcher_with_ledger.sh` was deployed from pinned release `f36836315526fd2be826e8abff1c333004b64b0c`, but its required `tools/watcher_persistence_gate.py` dependency was omitted from the deployment MANIFEST and absent at runtime. This caused every later open-market outer watcher cycle to terminate `INTERNAL_ERROR` with Python rc=2 / file-not-found.

2. `tools/telegram_send_guard.py` was deployed, but its imported module `tools/telegram_delivery.py` was not in the same 12-file deployment MANIFEST. Runtime logs later contain repeated:

```text
ModuleNotFoundError: No module named 'telegram_delivery'
```

The pinned sender executes `telegram_send_guard.py` before its network delivery boundary. Therefore this second missing dependency is a direct delivery-path failure candidate for accepted signals after Aug-16.

The Package-6 `RUNTIME_PARITY=PASS` was therefore a **manifest-parity false green**: the deployer verified only the files explicitly listed in its 12-item hard-coded MANIFEST and did not verify transitive runtime dependency closure.

## Trusted-clock forensic result

Phone wall clock and BotA trusted UTC disagreed by approximately 14 hours:

```text
PHONE_DATE_UTC=2026-09-03T20:33:35Z
PHONE_EPOCH=1788467615
TRUSTED_UTC=2026-09-03T06:34:44Z
TRUSTED_EPOCH=1788417284
DRIFT_SECONDS≈50331
```

`market_open.sh` used four HTTPS Date sources and returned:

```text
trusted_utc=2026-09-03T06:34:44Z
count=4
spread=1
reason=MARKET_CLOSED_ASIAN_PRE_0700
```

The drift report likewise showed four agreeing sources with 1–2 second spread and `local_clock_unsafe=true`.

An independent current-time check agreed with the trusted UTC, so the specific market-gate decision was correct on Sep-3.

Durable distinction:

```text
CURRENT_GATE_RESULT=CORRECT
TRUSTED_CLOCK_ARCHITECTURE=NOT_FULLY_INDEPENDENT
```

Four remote servers observed through one phone/network path are not four fully independent observation paths. This architectural weakness remains even though the sources were correct in this incident.

## Watcher terminal history

Read-only parsing of `logs/pipeline_events.jsonl` produced the following trusted-time daily terminal summary:

```text
2026-08-09  TERMINALS=287 MARKET_CLOSED=287
2026-08-10  TERMINALS=172 MARKET_CLOSED=118 INTERNAL_ERROR=4   EVALUATED_ACCEPTED=50
2026-08-11  TERMINALS=215 MARKET_CLOSED=103 INTERNAL_ERROR=5   EVALUATED_ACCEPTED=107
2026-08-12  TERMINALS=184 MARKET_CLOSED=58  INTERNAL_ERROR=12  EVALUATED_ACCEPTED=114
2026-08-13  TERMINALS=115 MARKET_CLOSED=79  INTERNAL_ERROR=5   EVALUATED_ACCEPTED=31
2026-08-14  TERMINALS=238 MARKET_CLOSED=129 INTERNAL_ERROR=6   EVALUATED_ACCEPTED=103
2026-08-15  TERMINALS=195 MARKET_CLOSED=195
2026-08-16  TERMINALS=139 MARKET_CLOSED=139
2026-08-17  TERMINALS=249 MARKET_CLOSED=131 INTERNAL_ERROR=118
2026-08-18  TERMINALS=210 MARKET_CLOSED=88  INTERNAL_ERROR=122
2026-08-19  TERMINALS=221 MARKET_CLOSED=115 INTERNAL_ERROR=106
2026-08-20  TERMINALS=187 MARKET_CLOSED=87  INTERNAL_ERROR=100
2026-08-21  TERMINALS=135 MARKET_CLOSED=89  INTERNAL_ERROR=46
2026-08-22  TERMINALS=231 MARKET_CLOSED=231
2026-08-23  TERMINALS=53  MARKET_CLOSED=53
2026-08-24  TERMINALS=139 MARKET_CLOSED=85  INTERNAL_ERROR=54
2026-08-25  TERMINALS=234 MARKET_CLOSED=90  INTERNAL_ERROR=144
2026-08-26  TERMINALS=59  MARKET_CLOSED=7   INTERNAL_ERROR=52
2026-08-27  TERMINALS=219 MARKET_CLOSED=90  INTERNAL_ERROR=129
2026-08-28  TERMINALS=130 MARKET_CLOSED=87  INTERNAL_ERROR=43
2026-08-29  TERMINALS=22  MARKET_CLOSED=22
2026-09-02  TERMINALS=195 MARKET_CLOSED=53  INTERNAL_ERROR=142
2026-09-03  TERMINALS=79  MARKET_CLOSED=79
```

Cycle accounting:

```text
START_ROWS=6450
TERMINAL_ROWS=6160
START_WITHOUT_TERMINAL=290
TERMINAL_WITHOUT_START=0
```

The important transition is:

```text
LAST_NORMAL_EVALUATED_DAY=2026-08-14
WEEKEND=2026-08-15..2026-08-16
FIRST_ALL_OPEN_WINDOW_INTERNAL_ERROR_DAY=2026-08-17
```

## Supabase independent ground truth

Direct read-only query of the connected BotA/ProfitLab Supabase project found exactly two `signals` rows created after Aug-8:

```text
2026-08-10T18:52:05Z  USDJPY BUY  CLOSED  result_pips=-15.00
2026-08-12T13:11:33Z  GBPUSD BUY  CLOSED  result_pips=-15.70
```

No later `signals` rows were present at query time.

Therefore:

```text
SIGNALS_STOPPED_ON_AUG8=FALSE
LAST_CONFIRMED_SUPABASE_SIGNAL=2026-08-12
```

The Aug-8 watcher observability refactor did not itself stop all signal publication.

## Aug-16 Package-6 deployment evidence

Historical deployment record:

```text
RUNTIME_RELEASE_PIN=f36836315526fd2be826e8abff1c333004b64b0c
DEPLOYMENT=PASS
RUNTIME_PARITY=PASS
RUNTIME_FILES_VERIFIED=12
```

The deployer `ops/transactional_phone_deploy.py` hard-codes this MANIFEST:

```text
tools/chart_generator.py
tools/chart_generator_core.py
tools/run_signal_watcher_with_ledger.sh
tools/signal_watcher_core.sh
tools/signal_watcher_pro.sh
tools/supabase_publish.py
tools/telegram_delivery_boundary.py
tools/telegram_send.sh
tools/telegram_send_guard.py
tools/watcher_cycle_contract.py
tools/watcher_evidence_retention.py
tools/watcher_pending_delivery_recovery.py
```

The verifier checks SHA-256/mode only for this enumerated metadata list plus coarse service/sentinel state. It does not compute or verify runtime dependency closure.

## Dependency-closure failure #1 — watcher persistence gate

Phone evidence after Package 6:

```text
tools/run_signal_watcher_with_ledger.sh   DISK=EXISTS
tools/watcher_persistence_gate.py         DISK=MISSING
tools/watcher_cycle_contract.py           DISK=EXISTS
tools/watcher_evidence_retention.py       DISK=EXISTS
```

The deployed wrapper contains:

```text
python3 "${TOOLS}/watcher_persistence_gate.py" ...
```

All four paths exist in pinned release `f36836315526fd2be826e8abff1c333004b64b0c`.

Open-market cycle evidence from Sep-2 repeatedly shows:

```text
INTERNAL_ERROR
MARKET_OPEN
run_rc=2
aggregate=DATA_FETCH_FAILED
python3: can't open file '.../tools/watcher_persistence_gate.py': [Errno 2] No such file or directory
```

The `DATA_FETCH_FAILED` aggregate label is misleading for these cycles; the actual terminal failure is a missing runtime dependency.

## Dependency-closure failure #2 — Telegram delivery module

Pinned release facts:

- `tools/telegram_send_guard.py` contains:

```python
from telegram_delivery import decision_matches, parse_message, row_dict
```

- `tools/telegram_delivery.py` exists in pinned release `f368363...`.
- Package-6 MANIFEST contains `telegram_send_guard.py` but does **not** contain `telegram_delivery.py`.
- `tools/telegram_send.sh` invokes `telegram_send_guard.py` before invoking `telegram_delivery_boundary.py`.

Runtime `logs/error.log` contains repeated:

```text
File ".../tools/telegram_send_guard.py", line 12, in <module>
    from telegram_delivery import decision_matches, parse_message, row_dict
ModuleNotFoundError: No module named 'telegram_delivery'
```

This is a second concrete example of the same deployment-system failure class: a selected runtime file was installed without its required local dependency.

Because the watcher delivery path publishes to Supabase only after successful Telegram send/transaction completion, failure in the Telegram guard can suppress both Telegram delivery and downstream Supabase publication for otherwise accepted GREEN signals.

## Retained Sep-2 cycle sample

Claude Code independently inspected one retained failure triplet:

```text
state/watcher_cycle.NGZPiR.log
state/watcher_telegram.8IS4rp.jsonl
state/watcher_supabase.lcZvBT.jsonl
```

That cycle showed:

- `signal_watcher_pro.sh` executed to completion;
- EURUSD, GBPUSD and USDJPY M15 were all evaluated;
- all three were rejected in that specific cycle with score 0 / non-tradeable direction;
- Telegram result file was empty;
- Supabase result file was empty;
- the missing persistence gate then returned Python rc=2;
- watcher contract still emitted PASS before the outer wrapper failed.

This sample proves the wrapper can fail **after** strategy evaluation. It does not prove all post-Aug-16 cycles had score 0.

## alerts.csv population audit

`logs/alerts.csv` contained 6,794 parsed rows.

Daily post-Aug-10 population:

```text
2026-08-10 rows=150 accepted=2 score0=118 score>0=32 BUY/SELL=32
2026-08-11 rows=323 accepted=0 score0=298 score>0=25 BUY/SELL=25
2026-08-12 rows=342 accepted=2 score0=309 score>0=33 BUY/SELL=33
2026-08-13 rows=93  accepted=2 score0=76  score>0=17 BUY/SELL=17
2026-08-14 rows=311 accepted=0 score0=299 score>0=12 BUY/SELL=12
2026-08-17 rows=344 accepted=1 score0=255 score>0=89 BUY/SELL=89
2026-08-18 rows=60  accepted=0 score0=47  score>0=13 BUY/SELL=13
2026-08-19 rows=646 accepted=1 score0=498 score>0=148 BUY/SELL=148
2026-08-20 rows=307 accepted=0 score0=215 score>0=92 BUY/SELL=92
2026-08-21 rows=52  accepted=0 score0=42  score>0=10 BUY/SELL=10
2026-08-23 rows=96  accepted=0 score0=94  score>0=2  BUY/SELL=2
2026-08-24 rows=111 accepted=0 score0=78  score>0=33 BUY/SELL=33
2026-08-25 rows=78  accepted=3 score0=49  score>0=29 BUY/SELL=29
2026-08-26 rows=305 accepted=8 score0=221 score>0=84 BUY/SELL=84
2026-08-27 rows=255 accepted=0 score0=229 score>0=26 BUY/SELL=26
2026-08-28 rows=362 accepted=2 score0=272 score>0=90 BUY/SELL=90
2026-09-02 rows=212 accepted=0 score0=196 score>0=16 BUY/SELL=16
2026-09-03 rows=224 accepted=0 score0=162 score>0=62 BUY/SELL=62
```

Pre/post comparison:

```text
PRE_2026-08-10..14:
  ROWS=1219
  ACCEPTED=6
  SCORE_ZERO=1100
  SCORE_NONZERO=119
  BUY_SELL=119

POST_2026-08-17+:
  ROWS=3052
  ACCEPTED=15
  SCORE_ZERO=2358
  SCORE_NONZERO=694
  BUY_SELL=694
```

Therefore the hypothesis that Package 6 caused the strategy layer to collapse into universal score=0/HOLD behavior is **false**. Accepted and nonzero BUY decisions continued after Aug-16.

## Delivery log evidence

`logs/error.log` contains historical successful Telegram/Supabase events as well as later failures. Important observed classes include:

```text
[supabase_publish] published ...
[supabase_publish] SKIP ... ACTIVE signal already open
[TELEGRAM] send failed: URLError
ModuleNotFoundError: No module named 'telegram_delivery'
```

Historical successes must not be used to prove the post-Aug-16 path was healthy. The relevant new failure is the repeated missing `telegram_delivery` import in the deployed guard.

## Corrected root-cause model

What is proven:

```text
AUG16_DEPLOYMENT_MANIFEST_INCOMPLETE=YES
RUNTIME_PARITY_FALSE_GREEN=YES
WATCHER_PERSISTENCE_GATE_DEPENDENCY_MISSING=YES
OPEN_MARKET_OUTER_CYCLES_FAIL_INTERNAL_ERROR=YES
POST_AUG16_STRATEGY_EVALUATION_CONTINUED=YES
POST_AUG16_ACCEPTED_ALERT_ROWS_EXIST=YES
TELEGRAM_GUARD_IMPORT_FAILURE_OBSERVED=YES
TELEGRAM_DELIVERY_MODULE_OMITTED_FROM_MANIFEST=YES
SUPABASE_ROWS_AFTER_AUG12=0
```

What is not yet fully proven:

```text
EVERY_POST_AUG16_ACCEPTED_SIGNAL_FAILED_FOR_THE_SAME_DELIVERY_REASON=UNKNOWN
EXACT_ACCEPTED_ROW_TO_TELEGRAM_FAILURE_MAPPING=NOT_YET_RECONSTRUCTED
EXACT_ACCEPTED_ROW_TO_SUPABASE_ATTEMPT_MAPPING=NOT_YET_RECONSTRUCTED
```

Strong causal chain requiring final per-cycle correlation:

```text
accepted decision
 -> telegram_send.sh
 -> telegram_send_guard.py
 -> import telegram_delivery
 -> ModuleNotFoundError
 -> Telegram transaction cannot complete
 -> watcher does not reach successful complete_delivery_transaction
 -> GREEN Supabase publication cannot complete
```

## Claude Code independent audit

A read-only Claude Code Termux audit independently concluded:

```text
FALSE_GREEN_CONFIRMED
```

It traced Package-6 parity to the 12-item hard-coded MANIFEST and confirmed no dependency-closure walker exists.

Claude also identified two additional dependencies omitted from the manifest but present on phone at stale blobs:

```text
tools/watcher_cycle_ledger.py
tools/pipeline_ledger.py
```

Their behavioral impact was not independently proven during this session and remains classified as possible runtime drift, not established root cause.

Claude's one-cycle conclusion that no post-Aug-16 signals were being generated was subsequently corrected by the 6,794-row alerts audit: 15 accepted rows exist post-Aug-17.

## Durable failure patterns

### Pattern A — Manifest parity is not runtime parity

Verifying only a manually selected payload can produce a false green when installed files invoke omitted dependencies.

Prevention:

```text
MANIFEST_PARITY != DEPENDENCY_CLOSURE_PARITY
```

Any future deployer must verify transitive local runtime dependencies before mutation and again after install.

### Pattern B — New helper deployed without imported module

A Python script can hash-match the release while remaining unusable if its local import dependency was not deployed.

### Pattern C — Wrapper terminal code misclassified as data failure

A generic outer mapping translated Python rc=2 from file-not-found into `DATA_FETCH_FAILED`, obscuring the real failure class.

### Pattern D — One retained cycle is not a period-wide behavioral sample

The sampled Sep-2 cycle had score=0/HOLD across all pairs, but the full alerts ledger proved many post-Aug-16 nonzero and accepted decisions.

### Pattern E — Delivery, publication and evaluation are separate evidence streams

An accepted decision in `alerts.csv` does not prove Telegram send, and Telegram success does not by itself prove Supabase publication.

## Recommended engineering-only follow-up

Do not tune strategy. Do not deploy to Hetzner Production. Do not reopen BotA validation.

If operational preservation continues, the next read-only task is to correlate all 15 post-Aug-17 accepted `alerts.csv` rows to contemporaneous watcher/Telegram/Supabase evidence and classify each as:

```text
LOW/YELLOW tier skip
cooldown suppressed
dedup suppressed
telegram guard/import failure
Telegram network failure
Supabase skipped due active signal
Supabase publish failure
successful publication
insufficient retained evidence
```

Only after that evidence is preserved should any runtime repair be considered.

## Evidence-handling rule

This audit intentionally excludes secret values and personal Telegram identifiers. Runtime logs may contain such values/IDs locally; do not copy them into repository evidence.

## Repository mutation scope

This record itself is documentation/governance only.

```text
STRATEGY_CHANGED=NO
THRESHOLDS_CHANGED=NO
RUNTIME_CHANGED=NO
PHONE_SERVICE_RESTARTED=NO
TELEGRAM_SENT_BY_THIS_RECORD=NO
SUPABASE_WRITTEN_BY_THIS_RECORD=NO
```
