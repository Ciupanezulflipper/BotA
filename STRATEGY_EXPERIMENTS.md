# BotA Strategy Experiments Register

> Single source of truth for all strategy, threshold, entry logic, and filter experiments.
> Sits alongside BOTLOG.md (narrative) — this file is the structured register only.
> Format: one experiment per block. Never delete rows — mark as REVERTED or BANNED.

---

## Column Definitions

| Field | Meaning |
|---|---|
| ID | EXP-NNN sequential |
| Date | When applied or discovered |
| Category | THRESHOLD / ENTRY / PAIR / FILTER / SCORING / SL-TP / DATA |
| Parameters | Exact variable names and old → new values |
| Pairs/TFs | Scope of the experiment |
| Reason | Why it was tried |
| Evidence | Backtest, live signals, or observation |
| Outcome | Numeric result if available |
| Verdict | ACCEPTED / REVERTED / INCONCLUSIVE / BANNED / ACTIVE / PENDING |
| Source | BOTLOG.md line N, GEM-NNN, commit hash, or STATE.json |

---

## DO-NOT-REPEAT LIST

Experiments explicitly banned or reverted with negative evidence. Reference the EXP-ID.

| EXP-ID | What was banned | Why |
|---|---|---|
| EXP-002 | FILTER_SCORE_MIN=55, TELEGRAM_TIER_GREEN_MIN=60 | Zero validation evidence. Found on untracked .env, origin unknown. Caused unvalidated signals to fire for unknown period. |
| EXP-005 | EMA crossover entry | Entry at crossover = exact institutional stop-hunt point. Live record 11W/34L pre-Option C. Formally discarded. |
| EXP-009 | USDJPY v1 live scope | Causing losses. Dropped same session as added. |

---

## ACTIVE DEFERRED EXPERIMENTS

Experiments approved for future testing but not yet started or not yet meeting promotion criteria.

| EXP-ID | Description | Promotion Criteria | Current Status |
|---|---|---|---|
| EXP-015 | ADX 15-20 shadow lane | ≥15 non-HOLD entries, score_partial≥52, ≤80% one-sided, D1 aligned | 1 entry captured. Criteria NOT MET. |
| EXP-029 | RSI exhaustion filter (GEM-99) H4 RSI<22 warning at score≥90 | 5 confirmed instances | 1/5 confirmed |
| EXP-030 | EMA200 macro trend filter (GEM-2) | Backtest run required | CANDIDATE — no backtest |
| EXP-033B | NEWS_ON=1 live enablement | Supportive H1 context + near-signal cycle observed | Blocked — open issue STATE.json |
| EXP-036B | USDJPY added to live watcher scope | EXP-015 promotion criteria met + separate explicit approval | Technical proof exists; live scope NOT approved |
| EXP-038 | Clean 14-signal performance baseline (excl. March 13 + March 19) | Final exclusion SQL query run against Supabase | Not yet computed |

---

## Experiments

---

### EXP-001

| Field | Value |
|---|---|
| **ID** | EXP-001 |
| **Date** | 2026-03-01 |
| **Category** | THRESHOLD |
| **Parameters** | FILTER_SCORE_MIN=62, FILTER_SCORE_MIN_ALL=62, TELEGRAM_MIN_SCORE=62, TELEGRAM_TIER_YELLOW_MIN=62, TELEGRAM_TIER_GREEN_MIN=65 |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | First validated threshold baseline. Set after full alerts.csv audit and ADX/H1/MTF gate wiring. |
| **Evidence** | Historical backtest: ADX>=20 + H1 not-opposite + score>=65. 53.3% WR, +252.5 pips. |
| **Outcome** | 53.3% WR / +252.5 pips |
| **Verdict** | ACCEPTED — superseded by EXP-003 |
| **Source** | BOTLOG.md line 13, line 92, line 102 |

---

### EXP-002

| Field | Value |
|---|---|
| **ID** | EXP-002 |
| **Date** | Unknown (discovered 2026-03-06) |
| **Category** | THRESHOLD |
| **Parameters** | FILTER_SCORE_MIN=55, TELEGRAM_TIER_GREEN_MIN=60 |
| **Pairs/TFs** | Unknown scope (untracked .env) |
| **Reason** | Unknown — zero documentation, zero validation |
| **Evidence** | Found on untracked .env file. Origin unresolvable. Change history lost as .env was untracked since commit 3dffe1e. |
| **Outcome** | Unknown — unvalidated signals fired for unknown duration |
| **Verdict** | **BANNED** — zero validation. Never use values below 62/65 without a dedicated backtest. |
| **Source** | BOTLOG.md line 371 |

---

### EXP-003

| Field | Value |
|---|---|
| **ID** | EXP-003 |
| **Date** | 2026-03-10 |
| **Category** | THRESHOLD |
| **Parameters** | FILTER_SCORE_MIN: 62→70, TELEGRAM_TIER_YELLOW_MIN: 62→70, TELEGRAM_TIER_GREEN_MIN: 65→75 |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | GEM-111. Raised after H1_neutral veto enabled (EXP-016). Pre-filter baseline was 51 signals at 25.5% WR / -264 pips — signals below 70 had no directional edge. |
| **Evidence** | 51 signals evaluated at 62/65 config: WR=25.5%, -264 pips. Root cause: H1_neutral signals with no directional edge. Crontab also had hardcoded 62/65 — fixed separately 2026-03-13. |
| **Outcome** | Expected WR improvement to 40-50%. Baseline post-change: 9W/9L provisional (EXP-037). |
| **Verdict** | ACTIVE |
| **Source** | BOTLOG.md line 438-450, GEM-111, commit area 2026-03-10 |

---

### EXP-004

| Field | Value |
|---|---|
| **ID** | EXP-004 |
| **Date** | 2026-03-23 |
| **Category** | THRESHOLD |
| **Parameters** | FILTER_SCORE_MIN: 70→65 (YELLOW/GREEN unchanged at 70/75) |
| **Pairs/TFs** | GBPUSD / M15 (EURUSD dropped same session) |
| **Reason** | Option C pullback entry (EXP-008) reduced signal frequency. FILTER_SCORE_MIN lowered to restore signal volume while keeping Telegram quality thresholds unchanged. |
| **Evidence** | Recorded in BOTLOG.md Session 2026-03-23. Signal volume was too low after pullback entry tightening. |
| **Outcome** | Volume restored. Not a WR-optimising change. |
| **Verdict** | ACTIVE |
| **Source** | BOTLOG.md line 508, commit b10f097 |

---

### EXP-005

| Field | Value |
|---|---|
| **ID** | EXP-005 |
| **Date** | Pre-2026-03-23 |
| **Category** | ENTRY |
| **Parameters** | Enter M15 signal at EMA crossover candle close |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | Original entry method — fire at the first candle confirming EMA cross |
| **Evidence** | Live record pre-Option C: 11W/34L. Root cause identified by 3 independent AIs (Grok, Gemini, ChatGPT-5): crossover = exact institutional stop-hunt point. |
| **Outcome** | 11W/34L live. Formally discarded 2026-04-01. |
| **Verdict** | **BANNED** — stop-hunting entry confirmed by live losses and AI consensus |
| **Source** | BOTLOG.md line 522, GEM-125 |

---

### EXP-006

| Field | Value |
|---|---|
| **ID** | EXP-006 |
| **Date** | 2026-03-19 |
| **Category** | ENTRY |
| **Parameters** | Option B H4 override: score>=90 AND M15 price breaks H4 EMA21 by 10+ pips in signal direction → bypass H4 opposing veto |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | GEM-124. Protect against missing high-conviction macro reversals (ECB/FOMC regime changes) where score>=90 but H4 cache not yet updated to new direction. |
| **Evidence** | March 19 ECB live test: score=100 but price was BELOW H4 EMA21 — override correctly did NOT fire. Confirms calibration tight enough. |
| **Outcome** | Override did not fire incorrectly in first real-world test. |
| **Verdict** | ACTIVE |
| **Source** | GEM-124, BOTLOG.md line 272 (GEMS.md), commit c779d7d |

---

### EXP-007

| Field | Value |
|---|---|
| **ID** | EXP-007 |
| **Date** | 2026-03-23 |
| **Category** | ENTRY |
| **Parameters** | Option C pullback buffer: ±0.5x ATR from EMA21 |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | GEM-125. Enter only when price pulls back to EMA21 zone and closes in trend direction. 0.5x ATR was initial buffer width. |
| **Evidence** | 90-day backtest: GBPUSD 46.2% WR +138.9 pips. EURUSD 23.1% WR LOSING. |
| **Outcome** | GBPUSD 46.2% WR / +138.9 pips. EURUSD 23.1% WR (led to EXP-011). |
| **Verdict** | REVERTED — tightened to 0.3x ATR (EXP-008) to reduce blockage |
| **Source** | GEM-125, BOTLOG.md line 502-506, commit 06dcdc7 |

---

### EXP-008

| Field | Value |
|---|---|
| **ID** | EXP-008 |
| **Date** | 2026-03-27 |
| **Category** | ENTRY |
| **Parameters** | Option C pullback buffer: ±0.5x ATR → ±0.3x ATR from EMA21 |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | Bot was getting blocked too frequently at 0.5x ATR — signal volume collapsed. 0.3x ATR restores tradeable frequency while keeping pullback confirmation logic. |
| **Evidence** | 90-day backtest post-tightening: 42.9% WR. Slight reduction from 46.2% at 0.5x but acceptable signal volume. |
| **Outcome** | 42.9% WR (90-day backtest) |
| **Verdict** | ACTIVE |
| **Source** | BOTLOG.md line 504 area, commit bfa4d7a, commit e4d51c0 |

---

### EXP-009

| Field | Value |
|---|---|
| **ID** | EXP-009 |
| **Date** | 2026-02-26 |
| **Category** | PAIR |
| **Parameters** | PAIRS: added USDJPY |
| **Pairs/TFs** | USDJPY / M15 |
| **Reason** | Diversification attempt |
| **Evidence** | Issue I-F02: USDJPY causing losses. Dropped same session as added. |
| **Outcome** | Net negative — causing losses |
| **Verdict** | **BANNED** (v1). See EXP-013 for v2 technical revalidation. |
| **Source** | BOTLOG.md line 92 (I-F02), DECISIONS.md |

---

### EXP-010

| Field | Value |
|---|---|
| **ID** | EXP-010 |
| **Date** | 2026-03-01 |
| **Category** | PAIR |
| **Parameters** | PAIRS: removed EURJPY, XAUUSD |
| **Pairs/TFs** | EURJPY, XAUUSD / M15 |
| **Reason** | Root audit 2026-03-01 found these pairs in PAIRS default — no evidence they were validated. BOTLOG.md cleanup. |
| **Evidence** | BOTLOG.md 2026-03-01 session: "Fixed signal_watcher_pro.sh PAIRS default (removed USDJPY/EURJPY)" |
| **Outcome** | Removed cleanly — no evidence of positive contribution |
| **Verdict** | REVERTED (removed permanently) |
| **Source** | BOTLOG.md line 91 |

---

### EXP-011

| Field | Value |
|---|---|
| **ID** | EXP-011 |
| **Date** | 2026-03-23 |
| **Category** | PAIR |
| **Parameters** | PAIRS: removed EURUSD |
| **Pairs/TFs** | EURUSD / M15 |
| **Reason** | 90-day backtest with Option C pullback entry showed EURUSD 23.1% WR LOSING. Strong macro uptrend meant pullback SELL setups kept losing (GEM-126). |
| **Evidence** | 90-day backtest: EURUSD 23.1% WR. GBPUSD 46.2% WR. |
| **Outcome** | EURUSD dropped. GBPUSD-only period. |
| **Verdict** | REVERTED — EURUSD re-added with D1 filter (EXP-012) on 2026-03-24 |
| **Source** | GEM-126, BOTLOG.md line 505-506, commit 9b65cb2 |

---

### EXP-012

| Field | Value |
|---|---|
| **ID** | EXP-012 |
| **Date** | 2026-03-24 |
| **Category** | PAIR |
| **Parameters** | PAIRS: re-added EURUSD with D1 EMA9/21 direction filter mandatory |
| **Pairs/TFs** | EURUSD / M15 |
| **Reason** | GEM-127. D1 trend filter expected to push EURUSD WR from 23% to 45-58% by only taking M15 signals aligned with daily trend. Research: D1 trend filter adds +10-25% WR on M15 strategies. |
| **Evidence** | At time of addition: EURUSD D1 trend=SELL. D1 filter live. As of 2026-04-24: D1 trend=BUY. |
| **Outcome** | Not independently backtested yet on EURUSD with D1 filter applied. |
| **Verdict** | ACTIVE |
| **Source** | GEM-127, GEM-128, BOTLOG.md Session 2026-03-23, commit 03880fb |

---

### EXP-013

| Field | Value |
|---|---|
| **ID** | EXP-013 |
| **Date** | 2026-04-01 |
| **Category** | PAIR |
| **Parameters** | USDJPY technical re-validation. D1 trend=BUY. Added to updater scope. Not added to live watcher. |
| **Pairs/TFs** | USDJPY / M15, H1, H4, D1 |
| **Reason** | Diversification — D1 BUY diverged from EURUSD/GBPUSD SELL at time of addition. Zero extra API cost as OANDA already fetching USDJPY. |
| **Evidence** | OANDA M15/H1/H4/D1 fetch/build OK. USDJPY sanity PASSED. Reboot proof 2026-04-24 confirmed pipeline healthy. |
| **Outcome** | Technical proof exists. Live scope NOT approved. |
| **Verdict** | PENDING — technical validation does not equal live approval. Locked out of watcher per DECISIONS.md 2026-04-22. |
| **Source** | BOTLOG.md Session 2026-04-01, DECISIONS.md 2026-04-22, STATE.json usdjpy_status |

---

### EXP-014

| Field | Value |
|---|---|
| **ID** | EXP-014 |
| **Date** | 2026-02-28 |
| **Category** | FILTER |
| **Parameters** | ADX hard gate: HOLD if ADX < 20. No signals emitted below this threshold. |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | I-04 fix. ADX<20 = ranging market, no directional edge. Validated baseline (53.3% WR) was computed with this gate active. |
| **Evidence** | Issue I-04 fix (BOTLOG.md). Baseline 53.3% WR / +252.5 pips used ADX>=20 as condition. Live proof: scoring_engine.sh lines 468-476 confirmed emitting zeroed HOLD payloads for ADX<20 (CONTINUITY.md 2026-04-21). |
| **Outcome** | 53.3% WR on backtest with gate active |
| **Verdict** | ACTIVE — gate locked at ADX>=20. Do not lower to <15 under any scenario. |
| **Source** | BOTLOG.md line 13 (issue I-04), GEM-89, CONTINUITY.md 2026-04-21, STATE.json scoring.adx_hard_gate |

---

### EXP-015

| Field | Value |
|---|---|
| **ID** | EXP-015 |
| **Date** | 2026-04-07 |
| **Category** | FILTER |
| **Parameters** | Shadow ADX lane: log full pre-gate payload for 15 <= ADX < 20 to logs/shadow_adx_scoring.jsonl. Production gate unchanged. |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | Observability improvement for ranging-edge regime. Capture whether ADX 15-20 signals have positive directional score before committing to live gate change. |
| **Evidence** | Installed commit 18f1f6c. First validated shadow entry 2026-04-07: USDJPY ADX=15.3, score_partial=47.4, blocked_lt20. Latest proven entry 2026-04-20: EURUSD ADX=18.6, score_partial=51.6, direction=BUY, d1_trend=BUY. |
| **Outcome** | score_partial=51.6 — below FILTER_SCORE_MIN=65. Context preservation improves observability but would NOT restore Telegram alerts by itself. |
| **Verdict** | PENDING — promotion criteria NOT MET. |
| **Source** | BOTLOG.md Session 2026-04-07, commit 18f1f6c, STATE.json shadow_adx_experiment, CONTINUITY.md 2026-04-21 |

**Promotion criteria (all required):**
- ≥ 15 non-HOLD entries in shadow log
- score_partial >= 52.0
- ≤ 80% one-sided (not all BUY or all SELL)
- D1 alignment confirmed

---

### EXP-016

| Field | Value |
|---|---|
| **ID** | EXP-016 |
| **Date** | 2026-03-10 |
| **Category** | FILTER |
| **Parameters** | H1_neutral veto: veto="false" → veto="true" for H1_trend_neutral. Two branches fixed: h1_dir=HOLD (m15_h1_fusion.sh line 245) and h1_filter_rejected (line 216). |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | GEM-110, GEM-113. H1 neutral signals had no directional edge — WR was 25.5% / -264 pips on 51 signals. Both branches independently left veto=false before fix. |
| **Evidence** | Pre-filter WR: 25.5% (-264 pips, 51 signals). GEM-113: first patch only fixed one branch — second branch also independently left veto=false. Expected volume cut: 60-70%. |
| **Outcome** | Signal volume reduced significantly. WR improvement expected. |
| **Verdict** | ACTIVE |
| **Source** | GEM-110, GEM-113, BOTLOG.md line 448-449, BOTLOG.md 2026-03-10 section |

---

### EXP-017

| Field | Value |
|---|---|
| **ID** | EXP-017 |
| **Date** | 2026-03-03 (initial), adjusted later |
| **Category** | FILTER |
| **Parameters** | H1_VETO_OVERRIDE_SCORE: hard veto → bypass H1 neutral veto if score >= 85 (initial, live session 2026-03-03) then adjusted to H1_VETO_OVERRIDE_SCORE=75 in strategy.env |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | GEM-98. Live observation 2026-03-03: GBPUSD score=98.20 blocked by H1 veto, ADX=50.8, RSI=15 — extreme trend with clear directional edge. High-conviction signals with extreme ADX should override neutral H1. |
| **Evidence** | Live: GBPUSD score=98.20, ADX=50.8, RSI=15 blocked. EURUSD score=95 also blocked. Both in extreme trend. First version: score>=85 AND ADX>=40. Current: score>=75 (H1_VETO_OVERRIDE_SCORE=75 in strategy.env — note: appears duplicated in strategy.env, cleanup needed). |
| **Outcome** | Unblocked high-conviction signals in extreme trend conditions. |
| **Verdict** | ACTIVE |
| **Source** | BOTLOG.md line 482, GEM-98, BOTLOG.md 2026-03-03 session table, strategy.env H1_VETO_OVERRIDE_SCORE=75 |

---

### EXP-018

| Field | Value |
|---|---|
| **ID** | EXP-018 |
| **Date** | 2026-03-16 |
| **Category** | FILTER |
| **Parameters** | H4 direction guard on H1 neutral override: pre-fetch H4 direction from indicators cache before fusion; block override when H4 opposes M15 direction regardless of score |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | GEM-117. H1 neutral override at score>=85 was allowing M15 signals against H4 trend. EURUSD BUY at 1.15018 fired against H4 SELL on 2026-03-16 — confirmed loss. |
| **Evidence** | Live loss: EURUSD BUY entry=1.15018 against H4 SELL. Root cause confirmed. Fix: H4 direction pre-fetched in m15_h1_fusion.sh, override blocked when H4 opposes. |
| **Outcome** | Counter-trend override losses eliminated. |
| **Verdict** | ACTIVE |
| **Source** | GEM-117, commit ea6e4b0 |

---

### EXP-019

| Field | Value |
|---|---|
| **ID** | EXP-019 |
| **Date** | 2026-03-16 |
| **Category** | FILTER |
| **Parameters** | Session filter: restrict signals to London + NY sessions only, 07:00–20:00 UTC. SKIP_SESSION_FILTER=0 (active). Override: SKIP_SESSION_FILTER=1 for testing. |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | GEM-115. Asian session signals = low liquidity, range-bound. Expected WR improvement: +5-10%. |
| **Evidence** | backtest_eurusd_sessions.py (GEM-57 archive): session filter analysis confirmed London/NY 13-17 UTC highest signal quality. |
| **Outcome** | Expected +5-10% WR. No standalone pre/post comparison available in sources. |
| **Verdict** | ACTIVE |
| **Source** | GEM-115, commit db988eb, strategy.env SKIP_SESSION_FILTER=0 |

---

### EXP-020

| Field | Value |
|---|---|
| **ID** | EXP-020 |
| **Date** | 2026-03-17 (v4 final) |
| **Category** | FILTER |
| **Parameters** | Calendar guard v4: TradingEconomics guest:guest (primary, free, HIGH impact only) + RapidAPI fallback (RAPIDAPI_CALENDAR_KEY). Fails open if unavailable. |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | GEM-120, GEM-121. Block signals around high-impact economic events. |
| **Evidence** | v1 (OANDA Labs): 403 on practice accounts (GEM-119). v2/v3: RapidAPI free tier too limited (commit 35209c4). v4: TradingEconomics free guest access confirmed working, RapidAPI fallback. Expected WR improvement: +2-5%. |
| **Outcome** | Calendar guard live. Fails open — no trading disruption if API unavailable. |
| **Verdict** | ACTIVE |
| **Source** | GEM-119, GEM-120, GEM-121, commits 3af416e, f6880fb |

---

### EXP-021

| Field | Value |
|---|---|
| **ID** | EXP-021 |
| **Date** | 2026-02-28 |
| **Category** | FILTER |
| **Parameters** | Pause guard: -3R daily loss on a pair → pair paused for session. Cron 06:05 UTC. |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | GEM-60. Circuit breaker to prevent runaway daily losses. |
| **Evidence** | I-10 fix. Wired in BOTLOG.md 2026-02-28 changelog. |
| **Outcome** | Circuit breaker installed. |
| **Verdict** | ACTIVE |
| **Source** | GEM-60, BOTLOG.md line 92 (I-10) |

---

### EXP-022

| Field | Value |
|---|---|
| **ID** | EXP-022 |
| **Date** | 2026-02-26 |
| **Category** | FILTER |
| **Parameters** | Dead zone guard: no signals 21:30–23:00 UTC. SKIP_DEAD_ZONE=0. |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | I-F04 fix. Rollover/dead zone at end of trading day: liquidity thin, spreads widen, FX market approaching close. |
| **Evidence** | Issue I-F04: "Dead zone 21:30-23:00 missing — FIXED 2026-02-26" (BOTLOG.md). |
| **Outcome** | Dead zone blocked. |
| **Verdict** | ACTIVE |
| **Source** | BOTLOG.md issue I-F04, strategy.env SKIP_DEAD_ZONE=0 |

---

### EXP-023

| Field | Value |
|---|---|
| **ID** | EXP-023 |
| **Date** | 2026-03-16 |
| **Category** | SCORING |
| **Parameters** | bb_comp added to scoring_engine.sh: BB squeeze=-10, band_touch+confluence=+8, midline_align=+3, counter=-5. Range: max +8, min -10. Parameters: 20-period SMA, 2 std dev. |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | GEM-116. Phase 4 scoring improvement. Bollinger Band position provides squeeze/expansion context. |
| **Evidence** | 90-day backtest at time of implementation: EURUSD +4.8% WR improvement, GBPUSD +5.1% WR improvement (commits ad66230, 94918ed). |
| **Outcome** | EURUSD +4.8% WR / GBPUSD +5.1% WR (90-day backtest) |
| **Verdict** | ACTIVE |
| **Source** | GEM-116, BOTLOG.md line 494 area, commits 94918ed, ad66230 |

---

### EXP-024

| Field | Value |
|---|---|
| **ID** | EXP-024 |
| **Date** | 2026-03-27 |
| **Category** | SCORING |
| **Parameters** | BB squeeze penalty: prior value → -3 pts (reduced magnitude). |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | BB squeeze penalty was too aggressive — blocking valid signals during low-volatility entry setups. Tightened alongside pullback tolerance change (EXP-008). |
| **Evidence** | Commit bfa4d7a: "BB squeeze -3pts". Commit e4d51c0: "42.9% WR 90-day backtest" after both EXP-008 and EXP-024 combined. |
| **Outcome** | Combined with EXP-008: 42.9% WR (90-day backtest) |
| **Verdict** | ACTIVE |
| **Source** | BOTLOG.md commit e4d51c0 message, commit bfa4d7a |

---

### EXP-025

| Field | Value |
|---|---|
| **ID** | EXP-025 |
| **Date** | 2026-03-17 |
| **Category** | SCORING |
| **Parameters** | Tick volume score: high=+5, low=-3, normal=0 added to scoring_engine.sh |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | GEM-118. Tier 1 Phase 5. Low tick volume at signal time = lower conviction. High tick volume = confirmation of directional move. |
| **Evidence** | 30-day backtest (combined with EXP-026 session quality and EXP-027 news alignment): GBPUSD -112 pips → +54 pips (+166 pip swing), WR 28.6% → 41.7%. |
| **Outcome** | +166 pip improvement / WR 28.6%→41.7% (30-day, combined with EXP-026 and EXP-027) |
| **Verdict** | ACTIVE |
| **Source** | GEM-118, BOTLOG.md line 494, commit 8fde90a |

---

### EXP-026

| Field | Value |
|---|---|
| **ID** | EXP-026 |
| **Date** | 2026-03-17 |
| **Category** | SCORING |
| **Parameters** | Session quality score: London+NY overlap=+5, London or NY single=+2, edge=0 added to scoring_engine.sh |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | GEM-118. Tier 1 Phase 5. Session overlap = highest institutional participation and directional follow-through. |
| **Evidence** | Same 30-day backtest as EXP-025. Combined result: GBPUSD WR 28.6%→41.7%. |
| **Outcome** | See EXP-025 combined result |
| **Verdict** | ACTIVE |
| **Source** | GEM-118, BOTLOG.md line 494, commit 8fde90a |

---

### EXP-027

| Field | Value |
|---|---|
| **ID** | EXP-027 |
| **Date** | 2026-03-17 |
| **Category** | SCORING |
| **Parameters** | News alignment score: macro6 output → asymmetric score adjustment -15 to +10. NEWS_ON controls whether news_sentiment.py is called (currently NEWS_ON=0/unset). |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | GEM-118. Tier 1 Phase 5. Macro news aligned with direction adds conviction; opposing macro is a strong negative signal. |
| **Evidence** | Same 30-day backtest as EXP-025. Combined: WR 28.6%→41.7%. Current blocker: NEWS_ON=0 → m15_h1_fusion.sh injects macro6=3/provider=off (bypasses news_sentiment.py). |
| **Outcome** | Component implemented. Currently dormant (NEWS_ON=0). Open issue in STATE.json. |
| **Verdict** | ACTIVE (component wired) / NEWS_ON enablement PENDING — see EXP-033B in deferred list |
| **Source** | GEM-118, BOTLOG.md line 494, STATE.json open_issues[0] news-on-disabled, commit 8fde90a |

---

### EXP-028

| Field | Value |
|---|---|
| **ID** | EXP-028 |
| **Date** | 2026-03-17 |
| **Category** | SCORING |
| **Parameters** | S/R proximity score (sr_comp): at key level=+8, near=+5, mild=+3, neutral=0, opposing zone=-5/-8. Gate: activates only when ADX>20. |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | GEM-122. Price near a key support/resistance level has meaningfully different R:R than price in open space. Regime gate (ADX>20) prevents application in ranging markets. |
| **Evidence** | sr_score.py detects swing highs/lows from H1 cache. SR_COMP passed via environment. Commit a1d64a9. |
| **Outcome** | Wired into live scoring pipeline. |
| **Verdict** | ACTIVE |
| **Source** | GEM-122, commit a1d64a9 |

---

### EXP-029

| Field | Value |
|---|---|
| **ID** | EXP-029 |
| **Date** | 2026-03-03 (first observation) |
| **Category** | SCORING |
| **Parameters** | RSI exhaustion filter: H4 RSI < 22 when score >= 90 → emit exhaustion warning (not a hard block — proposed as warning first) |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | GEM-99. High score + extremely oversold/overbought H4 RSI may indicate move exhaustion not continuation. |
| **Evidence** | Signal #13 Day 2 (score=95.90, entry=1.15540): SL hit after bounce from low. H4 RSI was <22. 1/5 confirmations. |
| **Outcome** | 1 confirmed instance. Need 5 before implementing. |
| **Verdict** | PENDING — 1/5 confirmation threshold |
| **Source** | GEM-99, SIGNALS_LOG.md signal #13 |

---

### EXP-030

| Field | Value |
|---|---|
| **ID** | EXP-030 |
| **Date** | Undated — candidate from archive audit |
| **Category** | SCORING |
| **Parameters** | EMA200 macro trend filter: require price on correct side of EMA200 before signal fires |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | GEM-2. EMA200 represents the long-term macro trend. Filtering against it on H1 or H4 may reduce counter-trend entries. |
| **Evidence** | Archive scoring.py gem (GEM-2). No backtest run. |
| **Outcome** | No evidence yet |
| **Verdict** | PENDING — CANDIDATE. No backtest run. |
| **Source** | GEM-2, GEMS.md line 2 |

---

### EXP-031

| Field | Value |
|---|---|
| **ID** | EXP-031 |
| **Date** | Pre-2026-03-16 |
| **Category** | SL-TP |
| **Parameters** | SCALP_SL_ATR_MULT=1.5, SCALP_TP_ATR_MULT=2.5, implied RR=1.67 |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | Original ATR-based SL/TP. Comment preserved in strategy.env: "Previous: SL=1.5x ATR, TP=2.5x ATR, RR=1.67" |
| **Evidence** | Phase comment in strategy.env. Superseded by Phase 3 (EXP-032). |
| **Outcome** | No standalone WR recorded for this configuration. |
| **Verdict** | REVERTED — superseded by EXP-032 |
| **Source** | strategy.env Phase 3 comment |

---

### EXP-032

| Field | Value |
|---|---|
| **ID** | EXP-032 |
| **Date** | 2026-03-16 |
| **Category** | SL-TP |
| **Parameters** | SCALP_SL_ATR_MULT: 1.5→2.0, SCALP_TP_ATR_MULT: 2.5→4.0, FILTER_RR_MIN=1.4 |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | Phase 3 wider SL/TP. Tighter stops were being hunted (linked to EXP-005/EXP-007 stop-hunting root cause). Wider stops allow pullback logic to work without premature stop-out. |
| **Evidence** | Comment in strategy.env: "New: SL=2.0x ATR, TP=4.0x ATR, RR=2.0". Applied same session as BB scoring and session filter. |
| **Outcome** | Still active. Provisional live RR ratio=1.9 (STATE.json performance baseline). |
| **Verdict** | ACTIVE |
| **Source** | strategy.env SCALP_SL_ATR_MULT=2.0 / SCALP_TP_ATR_MULT=4.0, commit ef13838 |

---

### EXP-033

| Field | Value |
|---|---|
| **ID** | EXP-033 |
| **Date** | 2026-02-28 |
| **Category** | SL-TP |
| **Parameters** | Pip caps: max SL=20 pips, max TP=40 pips (hard caps in scoring_engine.sh) |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | GEM-53 (archive atr_sltp_conservative.py). Protects against NFP spike SL blowout where ATR multipliers alone would produce excessive pip risk. |
| **Evidence** | GEM-53 documented. I-10 fix session wired multiple guards including pip caps. |
| **Outcome** | Hard cap prevents runaway SL on spike events. |
| **Verdict** | ACTIVE |
| **Source** | GEM-53, BOTLOG.md line 92 (2026-02-28 changelog) |

---

### EXP-034

| Field | Value |
|---|---|
| **ID** | EXP-034 |
| **Date** | 2026-03-03 |
| **Category** | SL-TP |
| **Parameters** | TELEGRAM_COOLDOWN_SECONDS: 3600→1800 |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | Live observation 2026-03-03: EURUSD score=95 blocked by cooldown during a strong trending move. 60-minute cooldown was too long for M15 continuation signals. |
| **Evidence** | Live: EURUSD price=1.16252 ADX=52.6 RSI=15.3 — extreme trend blocked. Fix applied mid-session. BOTLOG.md 2026-03-03 session table. |
| **Outcome** | Continuation signals in trending conditions unblocked. |
| **Verdict** | ACTIVE |
| **Source** | BOTLOG.md 2026-03-03 session table, strategy.env TELEGRAM_COOLDOWN_SECONDS=1800 |

---

### EXP-035

| Field | Value |
|---|---|
| **ID** | EXP-035 |
| **Date** | 2026-03-09 |
| **Category** | DATA |
| **Parameters** | data_fetch_candles.sh: primary provider Yahoo Finance → OANDA api-fxpractice.oanda.com. Yahoo retained as emergency fallback. |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | GEM-100. Yahoo stale bug proven twice in production: 36h stale 2026-02-20, 48h stale 2026-02-27. Yahoo is single point of failure, violates ToS, breaks ~monthly. OANDA is the live account provider — most reliable source. |
| **Evidence** | Yahoo stale bugs confirmed in BOTLOG.md 2026-03-04 section. OANDA switch: BOTLOG.md 2026-03-09. Provider logged in output: [FETCH] OK provider=oanda. |
| **Outcome** | Yahoo stale bug mitigated. |
| **Verdict** | ACTIVE |
| **Source** | GEM-100, BOTLOG.md 2026-03-09 section, commit area 2026-03-09 |

---

### EXP-036

| Field | Value |
|---|---|
| **ID** | EXP-036 |
| **Date** | 2026-04-19 |
| **Category** | DATA |
| **Parameters** | Yahoo 429 handling: curl/wget Yahoo fallback exits code 3 on HTTP 429. indicators_updater.sh skips retry on rc=3. Yahoo curl/wget fallback bounded with --max-time. |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | Yahoo fallback was hanging on slow connections and creating retry storms on 429 responses. indicators_updater.sh was retrying generic non-zero exits. |
| **Evidence** | CONTINUITY.md 2026-04-19: Yahoo returned HTTP 429 in 0.70s. data_fetch_candles.sh had no --max-time on Yahoo fallback. Manual updater run post-fix: fetch_fail_count=0, build_fail_count=0. RESOLVED.md 2026-04-21. |
| **Outcome** | Retry storm eliminated. fetch_fail_count=0 confirmed. |
| **Verdict** | ACTIVE |
| **Source** | CONTINUITY.md 2026-04-19, RESOLVED.md 2026-04-21/22, commits ad704fd, acb7e2e |

---

### EXP-037

| Field | Value |
|---|---|
| **ID** | EXP-037 |
| **Date** | 2026-03-25 (fixed) |
| **Category** | DATA |
| **Parameters** | D1 cache auto-refresh: refresh_d1_cache.sh standalone script runs every 4 hours via cron (0 */4 * * *). Covers EURUSD, GBPUSD, USDJPY, XAUUSD. |
| **Pairs/TFs** | EURUSD, GBPUSD, USDJPY, XAUUSD / D1 |
| **Reason** | GEM-128. Previous approach (bash variable inside Python heredoc) was broken. indicators_updater.sh hardcoded to EURUSD/GBPUSD only for D1. Standalone script fills the gap. |
| **Evidence** | GEM-128 fix committed 2026-03-25. Commit f17f4c5. CONTINUITY.md 2026-04-19 recovery: "D1 refresh ran and printed EURUSD: BUY / GBPUSD: BUY". |
| **Outcome** | D1 cache reliable. Last refresh 2026-04-24. |
| **Verdict** | ACTIVE |
| **Source** | GEM-128, BOTLOG.md Session 2026-03-25, commit f17f4c5, STATE.json pipeline.d1_cache |

---

### EXP-038

| Field | Value |
|---|---|
| **ID** | EXP-038 |
| **Date** | Frozen 2026-04-24 |
| **Category** | THRESHOLD |
| **Parameters** | Provisional live performance baseline (post-Option C, excl. March 13 bulk close): 18 organic signals. 9W/9L, WR=50.0%, avg win=+46.7p, avg loss=-24.6p, net=+198.1p, expectancy=+11.0p, PF=1.89, RR=1.9. |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | Commercial baseline measurement. March 13 bulk close (24 signals via signal_closer.py without guardrails) removed as contamination. March 19 batch (4 signals at exactly +60.0 pips in 1.5s — source unproven) still included. Dashboard WR=38% is contaminated. |
| **Evidence** | STATE.json profitlab_signals (frozen 2026-04-24). Commit ee474e9. March 13 root cause: signal_closer.py live default without guardrails (DECISIONS.md). March 19: unproven source. |
| **Outcome** | Provisional. Do NOT use for commercial claims. Full clean baseline requires excluding March 19 batch (4 IDs in STATE.json). |
| **Verdict** | INCONCLUSIVE — provisional pending March 19 exclusion query |
| **Source** | STATE.json profitlab_signals, commit ee474e9, DECISIONS.md signal_closer.py role |

---

### EXP-039

| Field | Value |
|---|---|
| **ID** | EXP-039 |
| **Date** | 2026-04-29 |
| **Category** | THRESHOLD |
| **Parameters** | Proposed FILTER_SCORE_MIN 65 → 55 |
| **Pairs/TFs** | EURUSD, GBPUSD / M15 |
| **Reason** | Investigate whether 55-64 near-miss band contained viable signals |
| **Evidence** | Supabase query on all organic closed signals (excluding 28 contamination IDs). Zero rows returned in 55-64 band. |
| **Outcome** | No data — gate blocked before supabase_publish.py so signals in this range were never inserted |
| **Verdict** | INCONCLUSIVE — zero published live Supabase data in 55-64 band. Cannot evaluate without shadow ADX log (not yet at promotion criteria) or a dedicated backtest. |
| **Do not retry until** | Shadow ADX promotion criteria met (15+ non-HOLD entries, score_partial>=52, ≤80% one-sided, D1 aligned) OR a clean backtest is run |
| **Source** | Supabase query 2026-04-29, STRATEGY_EXPERIMENTS.md session |

---

*Last updated: 2026-04-29. Sources: BOTLOG.md, GEMS.md, DECISIONS.md, RESOLVED.md, CONTINUITY.md, state/STATE.json, config/strategy.env, SIGNALS_LOG.md, git log --all. No entries invented — every row maps to a proven source.*
