# BotA — Operating Scope and Telegram Presentation

Date: **2026-09-11 UTC**
Status: **OWNER-LOCKED CURRENT DIRECTION**

## Purpose

BotA is not being replaced or rebuilt. The owner explicitly rejected a BotA2/rewrite lane.

BotA now has exactly two operating objectives.

## Objective 1 — prove BotA online during the open FX market and report professionally

BotA must first prove, from natural market-open execution, that the existing Hetzner runtime is actually scanning and evaluating all three configured pairs correctly:

- EURUSD
- GBPUSD
- USDJPY

The proof must come from real open-market watcher cycles, not synthetic/forced signals and not process-liveness alone.

Required proof:

```text
HETZNER_RUNTIME_ACTIVE=YES
MARKET_OPEN_NATURAL_CYCLES=YES
EURUSD_SCANNED=YES
GBPUSD_SCANNED=YES
USDJPY_SCANNED=YES
FRESH_PRICE_CONTEXT=YES
FRESH_INDICATORS=YES
ATR_VOLATILITY_CONTEXT_VALID=YES
DECISION_PATH_VALID=YES
SYSTEMATIC_PRODUCTION_POLICY_FAILURE=NO
SYSTEMATIC_ATR_ZERO_PATHOLOGY=NO
SYSTEMATIC_ENTRY_ZERO_PATHOLOGY=NO
SYSTEMATIC_MISSING_INDICATOR_PATHOLOGY=NO
```

Current deployed release under proof:

```text
RELEASE_SHA=e9e6bc31b1a0bba74a9947060372f7bd19ddaac3
RELEASE_TREE=6031cef811d07af5a27a95077f29b4164701697f
```

Once this natural market-open proof passes, engineering work stops unless a concrete reliability defect invalidates data collection.

### Telegram signal presentation

Qualified signals must be presented in a modern professional forex-channel style. Presentation changes must not alter qualification logic, thresholds, entry, stop, target, score, or any strategy semantics.

Telegram should receive only real BotA-calculated values.

#### BUY example

```text
🟢 BOTA · BUY SIGNAL

EUR/USD · M15

🎯 Entry: 1.16840
🛑 Stop Loss: 1.16680
💰 Take Profit: 1.17160
⚖️ R:R: 1:2.0

Signal Score: 78/100 🟢
Trend: Bullish
H1: Aligned ✓
ADX: 24.6
Session: London

Setup: Momentum + trend continuation

🕒 09:45 UTC · 11 Sep 2026
BOTA • EURUSD • M15
```

#### SELL example

```text
🔴 BOTA · SELL SIGNAL

GBP/USD · M15

🎯 Entry: 1.35210
🛑 Stop Loss: 1.35400
💰 Take Profit: 1.34830
⚖️ R:R: 1:2.0

Signal Score: 81/100 🟢
Trend: Bearish
H1: Aligned ✓
ADX: 22.8
Session: New York

Setup: Bearish momentum continuation

🕒 14:30 UTC · 11 Sep 2026
BOTA • GBPUSD • M15
```

#### Closed-trade example

```text
✅ TRADE CLOSED · TP HIT

EUR/USD · BUY
Entry 1.16840 → Exit 1.17160
Result: +2.0R

⏱ Duration: 3h 45m

BotA Performance
Today: 2W · 1L · +2.7R

BOTA • VERIFIED OUTCOME
```

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

### End-of-day report

At the end of each trading day BotA should send one concise modern Telegram report summarizing what actually happened.

Required content where evidence exists:

- date/session status;
- BotA online/healthy status during the market-open window;
- expected versus completed scans;
- per-pair scan/qualification counts;
- qualified signals generated;
- Telegram delivery results;
- closed outcomes and net R where resolved;
- active/open signals;
- data/runtime issues;
- exact release identity.

If there were zero valid signals, the report must say so explicitly, e.g.:

```text
0 signals — market scanned normally; no setup satisfied BotA policy.
```

A broken or incomplete day must never be described as a clean zero-signal day.

## Objective 2 — collect several months before strategy tuning

After market-open runtime proof passes, BotA enters **collect + report mode**.

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

Collect trustworthy evidence for several months before considering strategy changes.

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

Only after this prospective evidence exists should the owner consider adjusting or tweaking BotA.

## Immediate next action

```text
NEXT=FIRST_NATURAL_MARKET_OPEN_RUNTIME_AND_SCORING_PROOF
```

No rebuild, no new bot, no broad AI review, and no strategy optimization before that proof.