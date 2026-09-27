# BotA Execution Recovery PRD — 2026-09-27

Status: **FOUNDER-DIRECTED RECOVERY CONTRACT**
Repository: `Ciupanezulflipper/BotA`
Purpose: finish a small, reliable 3-pair signal system and stop open-ended architectural archaeology.

## 1. Product objective

BotA exists to do one job reliably:

```text
EURUSD / GBPUSD / USDJPY
        ↓
M15 market scan
        ↓
indicators + frozen strategy
        ↓
explicit PASS / REJECT decision
        ↓
qualified setup
   ├─→ real Telegram signal
   └─→ Supabase public.signals → ProfitLab signal feed
        ↓
SL/TP lifecycle
   ├─→ real Telegram closure
   └─→ ProfitLab status/result update
        ↓
real daily Telegram report
```

Telegram and ProfitLab are **independent user-visible delivery sinks**. A failure of one sink must not prevent the other sink from receiving/displaying the same qualified signal.

Anything that does not materially support this flow must justify its existence or be removed/bypassed from the production path.

## 2. Current proven runtime truth

Latest direct Hetzner proof collected 2026-09-23 UTC:

```text
HETZNER_SERVICE=ACTIVE
DEPLOYED_SHA=d81c0a3da3363089ed200e264ae066fdf15fb5ba
ORCHESTRATOR=RUNNING
PROCESS_LIVENESS=True
MARKET_DATA=UPDATING
PIPELINE=UPDATING
BOTA_R5_SHADOW=1
BOTA_REQUIRE_R5_SHADOW=1
REAL_TELEGRAM_SIDE_EFFECTS=SUPPRESSED
DAILY_SUMMARY_GATE_DRY_RUN=FORCED
DAILY_SUMMARY_SEND=FORCED_OFF
SUPABASE_SIDE_EFFECTS=SUPPRESSED
```

The runtime is not dead. Both required user-facing delivery sinks are currently blocked by the active shadow boundary.

## 3. Recovery principle

Do not spend another development cycle preserving complexity for its own sake.

Required sequence:

1. one bounded forensic/reduction pass;
2. identify the minimum production path;
3. reuse only proven-good components;
4. remove or bypass redundant layers from the active path;
5. implement the smallest bounded repair;
6. validate both delivery sinks and their failure isolation locally;
7. run one independent high-value review;
8. deploy once;
9. prove natural production delivery.

No repeated archaeology after the causal path is known.

## 4. Frozen product scope

Production scope for recovery:

- pairs: `EURUSD`, `GBPUSD`, `USDJPY` only;
- execution timeframe: `M15`;
- existing strategy logic initially frozen;
- existing H1/H4/D1 context may remain only where already required by the frozen strategy;
- no automatic broker execution;
- no live-money trading;
- ProfitLab signal display is required as the second independent delivery sink;
- no ProfitLab commercial expansion, pricing redesign, marketing work, or unrelated dashboard feature work during BotA recovery;
- Telegram remains a required delivery sink, not the sole delivery sink.

Do not add pairs, timeframes, indicators, marketing features, new dashboards, or strategy tuning during recovery.

## 5. Required production path

The final active production path must be understandable as:

```text
fetch
→ validate freshness
→ calculate indicators
→ evaluate strategy
→ write one durable decision/signal record
→ if qualified, fan out independently:
     ├─ Telegram
     └─ Supabase public.signals → ProfitLab
→ track open signal
→ update ProfitLab lifecycle/result
→ send Telegram closure
→ send daily Telegram report
```

Delivery independence is mandatory:

```text
TELEGRAM_FAILURE_MUST_NOT_BLOCK_PROFITLAB=YES
PROFITLAB_FAILURE_MUST_NOT_BLOCK_TELEGRAM=YES
BOTH_HEALTHY_EXACTLY_ONCE_PER_SINK=YES
PROFITLAB_RETRY_MUST_NOT_DUPLICATE_TELEGRAM=YES
```

A future engineer must be able to identify the exact file/function responsible for every arrow.

## 6. Existing ProfitLab path to preserve unless disproven

Current code already contains the intended second delivery path:

- `tools/profitlab_delivery.py` consumes newly appended accepted GREEN rows from `logs/alerts.csv` with its own durable byte cursor;
- `tools/supabase_publish.py` publishes ACTIVE signals to Supabase `public.signals` and performs pair-level ACTIVE deduplication;
- the VPS orchestrator schedules `profitlab_delivery.py` every minute;
- `tools/signal_closer.py` updates signal lifecycle/result fields in Supabase;
- the existing Lovable ProfitLab project reads the same Supabase project, supports EURUSD/GBPUSD/USDJPY, and listens for `signals` INSERT/UPDATE changes.

The recovery task is therefore not to rebuild ProfitLab. It is to make the BotA→Supabase→ProfitLab path truly live and prove it remains independent from Telegram delivery.

## 7. Acceptance contract

BotA is not finished until all are proven:

```text
BOTA_ACCEPTANCE_1=Hetzner scans EURUSD, GBPUSD, USDJPY every M15
BOTA_ACCEPTANCE_2=market data is fresh and timeframe-correct
BOTA_ACCEPTANCE_3=every scan produces an auditable terminal decision
BOTA_ACCEPTANCE_4=genuine qualified setup reaches real Telegram
BOTA_ACCEPTANCE_5=same genuine qualified setup becomes visible in ProfitLab
BOTA_ACCEPTANCE_6=Telegram failure does not block ProfitLab publication
BOTA_ACCEPTANCE_7=ProfitLab/Supabase failure does not block Telegram send and can catch up without duplicate Telegram
BOTA_ACCEPTANCE_8=SL/TP lifecycle/result becomes visible in ProfitLab and Telegram closure is delivered
BOTA_ACCEPTANCE_9=daily report reaches real Telegram even when qualified_signals=0
BOTA_ACCEPTANCE_10=service restart resumes cleanly without duplicate sends/publications
BOTA_ACCEPTANCE_11=duplicate suppression is proven independently per sink
BOTA_ACCEPTANCE_12=no fake/forced production signal is required for natural production acceptance
BOTA_ACCEPTANCE_13=GitHub and Obsidian describe the actual deployed runtime
```

Local failure-injection tests may prove sink independence. They do not substitute for the final natural production signal proof.

## 8. Telegram / ProfitLab presentation rule

Operational `SCAN DELAYED` / `SCAN RESTORED` messages are not the product acceptance criterion.

Required Telegram outputs:

- qualified trade signal;
- trade closure/result;
- daily end-of-day report;
- severe runtime failure only when operator action is useful.

Required ProfitLab outputs:

- qualified signal visible in the Signals feed;
- lifecycle status/result updates visible after closure/cancellation;
- no duplicate ACTIVE signal caused by retry/restart.

Do not spam HOLD, REJECT, normal heartbeat, or debug output into the public signal surfaces.

## 9. R5 shadow decision boundary

`BOTA_R5_SHADOW=1` is currently proven to suppress both real Telegram and Supabase/ProfitLab side effects.

Do not simply flip the flag without proving all side effects that would become live.

Recovery must choose the smallest architecture that makes the two approved delivery sinks live while keeping unrelated side effects bounded. The design must explicitly prove Telegram/Supabase failure isolation rather than coupling one sink's success to the other's availability.

## 10. AI execution contract

For this recovery package:

```text
CHATGPT=CONTROL_PLANE_AND_EVIDENCE_RECONCILER
CLAUDE_CODE=PRIMARY_IMPLEMENTATION_WRITER
CURSOR=EDITOR_VIEWER_OR_EXPLICIT_FALLBACK_WRITER
ASTRA_CODEX=ONE_BOUNDED_FINAL_RED_TEAM_REVIEW
CONCURRENT_IMPLEMENTATION_WRITERS=NO
```

Claude Code is selected for the first implementation pass because the active defect spans Python, Bash, the R5 network/credential boundary, systemd/orchestrator behavior, Telegram and Supabase side effects, and cross-sink crash/failure semantics.

Cursor must not concurrently rewrite the same candidate. Astra/Codex is not another archaeology pass and must not rewrite the project from scratch. It receives the exact candidate SHA, focused diff, tests, runtime boundary, and acceptance contract and attempts to disprove readiness.

If Astra finds a concrete defect, ownership returns to the implementation writer for one bounded repair pass, followed by focused re-validation. Do not start an AI carousel.

## 11. Stop-loss rules

- Maximum one broad forensic/reduction pass.
- Maximum two repair attempts on the same mechanism before reclassification.
- If the current architecture cannot reach the acceptance contract within the recovery timebox, preserve strategy/evidence and implement a lean execution path rather than continuing to patch layers.
- Do not spend Hetzner time indefinitely on an intentionally silent configuration.

## 12. Evidence and secrets

GitHub/Obsidian may contain:

- SHA/state evidence;
- safe runtime flags;
- credential `PRESENT/MISSING/INVALID` state;
- short fingerprints;
- logs with secret values removed.

Never commit Telegram tokens, Supabase keys, OANDA tokens, passwords, or SSH private keys.

## 13. Definition of done

```text
BOTA_RECOVERY_DONE=YES
THREE_PAIR_SCAN=PASS
NATURAL_DECISION_RECORDING=PASS
REAL_TELEGRAM_SIGNAL_PATH=PASS
REAL_PROFITLAB_SIGNAL_PATH=PASS
TELEGRAM_FAILURE_ISOLATION=PASS
PROFITLAB_FAILURE_ISOLATION=PASS
REAL_TELEGRAM_CLOSE_PATH=PASS
REAL_PROFITLAB_LIFECYCLE_PATH=PASS
REAL_DAILY_REPORT=PASS
RESTART_RECOVERY=PASS
DEDUP_PER_SINK=PASS
RUNTIME_DOC_SYNC=PASS
LIVE_MONEY_TRADING=NO
```

Until this block is true, BotA is not finished.

## 14. Supersession relationship

Historical PRDs, audits and strategy evidence remain historical truth for their dates. This recovery PRD governs the **forward execution objective and acceptance criteria** from 2026-09-27 onward. Where an older operating document encourages preserving complexity that is not required for this acceptance contract, this recovery PRD controls the recovery scope.