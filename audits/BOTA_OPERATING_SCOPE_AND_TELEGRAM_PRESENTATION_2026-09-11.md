# BotA — Operating Scope and Telegram Presentation

Date: **2026-09-11 UTC**  
Verification update: **2026-09-15 UTC**  
Status: **OWNER-LOCKED CURRENT DIRECTION / NATURAL RUNTIME PROVEN**

## Purpose

BotA is not being replaced or rebuilt. The owner explicitly rejected a BotA2/rewrite lane.

BotA has two operating objectives:

1. prove the existing Hetzner runtime works naturally during the open FX market and report professionally;
2. collect several months of trustworthy evidence before strategy tuning.

## Objective 1 — natural open-market runtime proof

Required natural evidence was defined for:

- EURUSD;
- GBPUSD;
- USDJPY;
- M15 decision evaluation;
- real open-market watcher cycles;
- no forced/synthetic signal requirement.

### Verification result — 2026-09-15

The exact deployed PR #134 head was observed live:

```text
RELEASE_SHA=d81c0a3da3363089ed200e264ae066fdf15fb5ba
RELEASE_TREE=c083de54f407061d6b744b26b51e1f3fab4212a2
CONFIG_FINGERPRINT=c9b636e1597743df11daa439f37b311e2434c7bc2ce7589e306739b6207e1b7b
BOTA_SERVICE=active
ORCHESTRATOR_LIFECYCLE=RUNNING
ORCHESTRATOR_LIVENESS=PASS
```

Natural evidence since the FX reopen anchor `2026-09-13T21:05:00Z`:

```text
POST_REOPEN_EVENTS=2390
MALFORMED_LEDGER_ROWS=0
MARKET_OPEN_COMPLETED_CYCLES=212
EURUSD_M15_DECISIONS=212
GBPUSD_M15_DECISIONS=212
USDJPY_M15_DECISIONS=212
THREE_PAIR_COMPLETE_CYCLES=212
THREE_PAIR_SCAN_GATE=PASS
NATURAL_RUNTIME_GATE=PASS
POST_REOPEN_NON_FILTER_REJECTED=0
```

All 212 observed market-open terminal watcher outcomes were `EVALUATED_REJECTED`. This is valid no-signal operation, not a runtime failure.

Therefore:

```text
HETZNER_RUNTIME_ACTIVE=YES
MARKET_OPEN_NATURAL_CYCLES=YES
EURUSD_SCANNED=YES
GBPUSD_SCANNED=YES
USDJPY_SCANNED=YES
DECISION_PATH_VALID=YES
NATURAL_RUNTIME_GATE=PASS
```

The full proof is recorded in:

`audits/BOTA_PR134_POST_DEPLOY_RUNTIME_PROOF_2026-09-15.md`

## Telegram signal presentation

Qualified signals must be presented in a modern professional forex-channel style. Presentation changes must not alter qualification logic, thresholds, entry, stop, target, score, or any strategy semantics.

Only real BotA-calculated values may be displayed.

Rules:

```text
QUALIFIED_SIGNAL_TELEGRAM=YES
TRADE_CLOSED_TELEGRAM=YES
HOLD_TELEGRAM=NO
REJECT_TELEGRAM=NO
DEBUG_OUTPUT_TELEGRAM=NO
FAKE_CONFIDENCE_OR_MARKETING_CLAIMS=NO
```

HOLD/REJECT decisions remain in the evidence ledger so silence can be distinguished from valid no-signal behavior.

Because the inspected post-reopen window contained zero genuine qualifying setups, the deployed qualified-signal Telegram presentation path has not yet been naturally exercised. Do not force a signal to prove it.

## End-of-day report

The modern daily-report renderer was proven against live production evidence on 2026-09-15:

```text
Runtime: ONLINE
Market-open watcher cycles: 56
EUR/USD: 56 scans, 0 qualified
GBP/USD: 56 scans, 0 qualified
USD/JPY: 56 scans, 0 qualified
Qualified setups: 0
All 3 pairs observed: YES
Runtime issues: None observed
TELEGRAM_SEND=SKIPPED
```

The report correctly stated:

```text
0 signals — market scanned normally; no setup satisfied BotA policy.
```

### Daily-summary delivery blocker

Actual scheduled Telegram delivery is not yet proven.

Observed gate evidence:

```text
2026-09-12 20:10 UTC GATE_DRY_RUN would_send=YES
2026-09-13 20:10 UTC GATE_DRY_RUN would_send=YES
2026-09-14 20:10 UTC GATE_DRY_RUN would_send=YES
DAILY_SUMMARY_SENT_MARKER=ABSENT
```

The deployed gate enters this path only when `DAILY_SUMMARY_GATE_DRY_RUN=1` is present. The frozen `config/production-vps.env` does not define that key.

Current classification:

```text
DAILY_REPORT_RENDER=PASS
DAILY_REPORT_GATE_TIMING=PASS
DAILY_REPORT_ACTUAL_TELEGRAM_SEND=NOT_PROVEN
DAILY_SUMMARY_RUNTIME_MODE=DRY_RUN
DRY_RUN_ORIGIN=RUNTIME_AMBIENT_ENVIRONMENT_NOT_YET_LOCATED
```

Do not silently disable dry-run. Locate its provenance read-only first. Any production mutation enabling real scheduled daily Telegram sends requires explicit owner authorization.

## Objective 2 — collect several months before strategy tuning

The natural runtime gate has passed, so BotA is in **COLLECT_AND_REPORT** mode.

During this period:

```text
STRATEGY_TUNING=NO
THRESHOLD_TUNING=NO
PAIR_CHANGES=NO
TIMEFRAME_CHANGES=NO
H1_H4_D1_RULE_CHANGES=NO
SL_TP_STRATEGY_CHANGES=NO
FORCED_SIGNAL_GENERATION=NO
RELIABILITY_FIXES_IF_DATA_INVALID=YES
```

Collect trustworthy prospective evidence for several months before considering strategy changes.

Future analysis should evaluate at minimum:

- signal count and frequency;
- win/loss/open outcomes;
- Net R after realistic execution costs where measurable;
- pair-level performance;
- score-band performance;
- ADX/regime performance;
- long/short performance;
- session/time-of-day performance;
- rejection reasons;
- delivery reliability;
- missing-scan/data-quality incidents.

## PR #134 state

As checked on 2026-09-15:

```text
PR134_STATE=OPEN
PR134_DRAFT=YES
PR134_MERGEABLE=YES
PR134_MERGED=NO
PR134_HEAD=d81c0a3da3363089ed200e264ae066fdf15fb5ba
```

The exact PR head is deployed. Merge remains a separate action and is not authorized by the deployment approval.

## Immediate next action

```text
NEXT=READ_ONLY_DAILY_SUMMARY_DRY_RUN_PROVENANCE_CHECK
```

No rebuild, no new bot, no broad AI review, no strategy optimization, no forced signal, and no PR merge as part of this next proof step.