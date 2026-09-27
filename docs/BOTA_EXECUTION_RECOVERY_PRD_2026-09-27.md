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
qualified setup → real Telegram signal
        ↓
SL/TP lifecycle → real Telegram closure
        ↓
daily real Telegram report
```

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

The runtime is not dead. User-facing delivery is not operational.

## 3. Recovery principle

Do not spend another development cycle preserving complexity for its own sake.

Required sequence:

1. one bounded forensic/reduction pass;
2. identify the minimum production path;
3. reuse only proven-good components;
4. remove or bypass redundant layers from the active path;
5. implement the smallest bounded repair;
6. validate locally;
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
- no commercial ProfitLab dependency;
- private analytics may remain only if they do not block delivery;
- Telegram is the required user-facing delivery channel.

Do not add pairs, timeframes, indicators, marketing features, new dashboards, or strategy tuning during recovery.

## 5. Required production path

The final active production path must be understandable as:

```text
fetch
→ validate freshness
→ calculate indicators
→ evaluate strategy
→ write one decision record
→ if qualified, send Telegram
→ track open signal
→ send closure
→ send daily report
```

A future engineer must be able to identify the exact file/function responsible for every arrow.

## 6. Acceptance contract

BotA is not finished until all are proven:

```text
BOTA_ACCEPTANCE_1=Hetzner scans EURUSD, GBPUSD, USDJPY every M15
BOTA_ACCEPTANCE_2=market data is fresh and timeframe-correct
BOTA_ACCEPTANCE_3=every scan produces an auditable terminal decision
BOTA_ACCEPTANCE_4=genuine qualified setup reaches real Telegram
BOTA_ACCEPTANCE_5=SL/TP closure reaches real Telegram
BOTA_ACCEPTANCE_6=daily report reaches real Telegram even when qualified_signals=0
BOTA_ACCEPTANCE_7=service restart resumes cleanly without duplicate sends
BOTA_ACCEPTANCE_8=duplicate suppression is proven
BOTA_ACCEPTANCE_9=no fake/forced production signal is required for acceptance
BOTA_ACCEPTANCE_10=GitHub and Obsidian describe the actual deployed runtime
```

No internal green test substitutes for these product-level gates.

## 7. Telegram rule

Operational `SCAN DELAYED` / `SCAN RESTORED` messages are not the product acceptance criterion.

Required Telegram outputs:

- qualified trade signal;
- trade closure/result;
- daily end-of-day report;
- severe runtime failure only when operator action is useful.

Do not spam HOLD, REJECT, normal heartbeat, or debug output.

## 8. R5 shadow decision boundary

`BOTA_R5_SHADOW=1` is currently proven to suppress the real Telegram/Supabase side-effect path.

Do not simply flip the flag without proving all side effects that would become live.

Recovery must choose one of two architectures:

A. safely retire R5 shadow from the production runtime with explicitly bounded live side effects; or
B. keep R5 protection for unrelated effects and isolate the approved Telegram/analytics sender outside that sandbox.

The simpler architecture wins if both meet the same safety guarantees.

## 9. AI execution contract

For this recovery package:

```text
CHATGPT=CONTROL_PLANE_AND_EVIDENCE_RECONCILER
CURSOR_CLAUDE_CODE=PRIMARY_IMPLEMENTATION_LANE
ASTRA_CODEX=ONE_BOUNDED_FINAL_RED_TEAM_REVIEW
CONCURRENT_IMPLEMENTATION_WRITERS=NO
```

Cursor/Claude Code owns implementation. Astra/Codex is not another archaeology pass and must not rewrite the project from scratch. It receives the exact candidate SHA, focused diff, tests, runtime boundary, and acceptance contract and attempts to disprove readiness.

If Astra finds a concrete defect, ownership returns to Cursor for one repair pass, followed by focused re-validation. Do not start an AI carousel.

## 10. Stop-loss rules

- Maximum one broad forensic/reduction pass.
- Maximum two repair attempts on the same mechanism before reclassification.
- If the current architecture cannot reach the acceptance contract within the recovery timebox, preserve strategy/evidence and implement a lean execution path rather than continuing to patch layers.
- Do not spend Hetzner time indefinitely on an intentionally silent configuration.

## 11. Evidence and secrets

GitHub/Obsidian may contain:

- SHA/state evidence;
- safe runtime flags;
- credential `PRESENT/MISSING/INVALID` state;
- short fingerprints;
- logs with secret values removed.

Never commit Telegram tokens, Supabase keys, OANDA tokens, passwords, or SSH private keys.

## 12. Definition of done

```text
BOTA_RECOVERY_DONE=YES
THREE_PAIR_SCAN=PASS
NATURAL_DECISION_RECORDING=PASS
REAL_TELEGRAM_SIGNAL_PATH=PASS
REAL_TELEGRAM_CLOSE_PATH=PASS
REAL_DAILY_REPORT=PASS
RESTART_RECOVERY=PASS
DEDUP=PASS
RUNTIME_DOC_SYNC=PASS
LIVE_MONEY_TRADING=NO
```

Until this block is true, BotA is not finished.

## 13. Supersession relationship

Historical PRDs, audits and strategy evidence remain historical truth for their dates. This recovery PRD governs the **forward execution objective and acceptance criteria** from 2026-09-27 onward. Where an older operating document encourages preserving complexity that is not required for this acceptance contract, this recovery PRD controls the recovery scope.