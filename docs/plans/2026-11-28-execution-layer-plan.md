# BotA Execution Layer Plan (draft)

- Date: 2026-11-28
- Status: PLANNING ONLY. No code, no broker accounts, no money. Founder decision pending on the live broker.
- Author: Claude (reviewer), at founder's request. Not yet reviewed by ChatGPT.
- Depends on: production retirement complete (Telegram rotation, 72h clean-producer window, real signal lifecycle) and repair branch `fix/retirement-d1-active-signal-tests-20261125` deployed (new generation).

## Purpose

Add automatic order execution next to BotA's signal pipeline. First goal is **measurement, not profit**: real broker spreads, fills and slippage, which the Yahoo-based ledger cannot provide (mid prices only, TP-before-SL same-candle ambiguity).

## Principles

1. Demo first. Real money only after pre-registered gates pass.
2. One admitted signal = one order. The executor consumes the existing exposure gate (`tools/open_exposure.py`); it never makes its own entry decisions.
3. The executor is a small new BotA job on Hetzner, not a transplanted framework.
4. No LLM or "decision engine" in the trade path. Speed is not BotA's bottleneck; edge is.
5. Broker-side stop-loss and take-profit attached to every order. No naked positions.
6. Live money must survive the founder being unreachable (ship contracts): kill switch, daily loss limit, heartbeat-triggered auto-flatten.

## Broker landscape (EU / Romanian resident)

| Option | API | Status for us | Notes |
|---|---|---|---|
| XTB | none | NOT POSSIBLE | API discontinued 14 Mar 2025. |
| OANDA EU (OANDA TMS) | v20 REST: demo only | DEMO ONLY | v20 API not available for OANDA TMS live accounts. Existing practice token works today. |
| Interactive Brokers (IBKR Ireland) | TWS API, Web API, FIX | CANDIDATE #1/#2 | Accepts Romanian residents. API usable on funded accounts without approval. Needs IB Gateway running (Java; can run headless on Linux). Same account could later automate stock strategies (Catalyst/AlphaForge). Check forex lot-size pricing for small orders. |
| cTrader broker, EU entity (e.g. Pepperstone EU, IC Markets EU) | cTrader Open API (language-neutral) | CANDIDATE #1/#2 | Forex-native, micro lots, free demo on the same API as live. Must confirm the EU entity offers cTrader + Open API to Romanian retail. |
| Dukascopy Europe | JForex (Java), FIX | ALTERNATIVE | EU-licensed, real tick-data history. Java stack is a poor fit for BotA. |
| MT5 brokers | MetaTrader5 Python package | LAST RESORT | Python package is Windows-only; conflicts with the Linux Hetzner host. |
| Saxo | OpenAPI | NOT RECOMMENDED | Personal-use API oriented to portfolio tooling; automation tier-gated. |

**Key decision:** choose the live broker before building Phase A, and run Phase A on *that broker's demo* if it has one. Building on OANDA practice and then switching broker means writing two adapters (~15-25 h wasted). OANDA practice remains the fallback if the live-broker demo is unavailable.

All eligibility details must be re-verified at account opening.

## Phases and effort

Effort = engineering hours / hours in our workflow (founder as Lead Architect, ChatGPT building, Claude auditing; roughly 2-3x engineering time).

### Phase A: demo executor (10-15 h / 25-40 h)
- Consume admitted GREEN signals (exposure ID) and place a demo market order with SL/TP attached.
- Idempotency: exposure/signal ID used as the broker client order ID; a retry can never create a second order.
- Reconciler: broker positions vs. ledger vs. open-exposure records; mismatches raise a health alert.
- Record per trade: signal price, fill price, spread at entry, slippage, broker close reason and price.
- Kill switch (file or env flag) checked before every order.
- Offline tests against a mocked broker; no production deploy without founder approval.

### Phase B: demo evidence (1-2 h/week, 4-8 weeks)
- Weekly comparison: broker outcomes vs. ledger outcomes (quantifies TP-before-SL bias and cost drag).

### Phase C: small live (15-25 h / 30-60 h, only if gates pass)
- Live broker adapter (or switch of credentials if Phase A already ran on the target broker's demo).
- Position sizing from a fixed risk per trade, daily loss limit, max open positions.
- Heartbeat-triggered auto-flatten, manual arm/disarm switch, secrets in `/etc/bota` with the same atomic-replacement procedure as the Supabase/Telegram rotations.
- KYC/account opening and funding by founder.

Total to small live: ~60-100 workflow hours plus account setup; 2-3 months calendar time.

## Go-live gates (pre-registered; all must pass)

1. >= 30 independent episodes under the new generation (post-repair deploy).
2. Positive expectancy after demo-measured spread and slippage.
3. Beats a random-entry baseline with identical SL/TP geometry.
4. Demo broker outcomes match the signal ledger within an agreed tolerance.
5. Maximum drawdown within a budget the founder sets before Phase B starts.

Win rate alone is NOT a gate: with BotA's ~1.8 average win/loss ratio, a 60% win rate would be extraordinary and ~40% can already be profitable.

Live capital: only an amount the founder can afford to lose entirely.

## Agent Loop allocation

Agent Loop development is frozen pending the 28 Nov 2026 benchmark. If unfrozen, suitable bounded jobs:
- Broker adapter client and mocked-API unit tests.
- Reconciler logic and its tests.
- Documentation and continuity updates.

Never delegated to Agent Loop: credentials, account opening, BotFather/broker portals, production deploys, live-money configuration, gate acceptance.

Expected saving: ~20-30% of workflow hours (review and acceptance time does not shrink).

## Open founder decisions

1. Live broker shortlist: IBKR vs. a cTrader EU broker (verify eligibility, demo availability, small-lot pricing).
2. Run Phase A on the chosen broker's demo (recommended) or on OANDA practice.
3. Drawdown budget and live capital amount (before Phase B).
4. Whether Agent Loop is unfrozen for the bounded jobs above.

## Rejected for now

- LLM/"Jev"-style decision engines in the trade path (adds an unvalidated component; speed irrelevant at M15).
- Cloning a full trading framework (Lean, NautilusTrader, Backtrader, Freqtrade/Hummingbot/Jesse are crypto or heavy).

## Sources

- XTB API discontinued: https://www.xtb.com/en/help-center/our-platforms-5/does-xtb-offer-investment-automation-tools
- OANDA v20 availability by division: https://developer.oanda.com/rest-live-v20/introduction/
- QuantConnect note on OANDA TMS (EU): https://www.quantconnect.com/docs/v2/our-platform/live-trading/brokerages/oanda
- IBKR API types and access: https://www.interactivebrokers.com/support/faq/articles/614720743
- IBKR accepts Romanian residents: https://brokerchooser.com/broker-reviews/interactive-brokers-review/interactive-brokers-romania
- cTrader brokers in Romania / Open API: https://brokerchooser.com/best-brokers/best-brokers-for-ctrader-in-romania
- Dukascopy Europe JForex/FIX: https://www.dukascopy.com/europe/english/about/company/
- Saxo OpenAPI personal use: https://saxobank.zendesk.com/hc/en-us/articles/4416505486481-Can-I-use-OpenAPI-for-personal-use
