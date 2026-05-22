# BotA Pre-Commercial Checkpoint Audit — 2026-05-22

**Audit type:** Read-only inspection. No production files modified.
**Branch at audit:** `main` HEAD `20e23a5`
**Conducted:** 2026-05-22

---

## Purpose

Checkpoint before the `feat/signal-product-message-v1` branch is opened.
Confirms the state of all implemented features and identifies risks and unknowns
prior to adding any commercial signal-product messaging layer.

---

## 1. Signal Pipeline

| Item | State |
|------|-------|
| Pipeline status | ACTIVE |
| Active scan pairs | EURUSD, GBPUSD (M15) |
| USDJPY | Indicators fetched and cached by `tools/indicators_updater.sh`; **not confirmed in active signal scan cron** |
| Scan timeframes | M15 only |
| DRY_RUN_MODE | 0 (live) |

Evidence:
- Live crontab: `PAIRS="EURUSD GBPUSD" TIMEFRAMES="M15"`
- `config/pairs.txt`: EURUSD, GBPUSD
- `config/strategy.env`: DRY_RUN_MODE=0, TELEGRAM_ENABLED=1

---

## 2. Signal Thresholds — Confirmed Unchanged

| Threshold | Value | Source |
|-----------|-------|--------|
| FILTER_SCORE_MIN | 65 | `config/strategy.env:3`, live crontab |
| TELEGRAM_MIN_SCORE (YELLOW) | 70 | `config/strategy.env:6`, live crontab |
| TELEGRAM_TIER_GREEN_MIN | 75 | `config/strategy.env:8`, live crontab |
| H1_VETO_OVERRIDE_SCORE | 75 | `config/strategy.env:25-26` (duplicate line, both 75) |
| TELEGRAM_COOLDOWN_SECONDS | 1800 | `config/strategy.env:10`, live crontab |
| SCALP_SL_ATR_MULT | 2.0 | `config/strategy.env:22` |
| SCALP_TP_ATR_MULT | 4.0 | `config/strategy.env:23` |
| FILTER_RR_MIN | 1.4 | `config/strategy.env:24` |
| CANDLE_MAX_AGE_SECS | 2700 | live crontab |

---

## 3. H1 Veto — Hard in Implementation

**File:** `tools/m15_h1_fusion.sh` lines 250–379

- H1 direction opposite to M15 → `veto="true"` → output sets `filter_rejected=true`, appends `vetoed_by_H1`
- Override requires BOTH: `m15_score >= H1_VETO_OVERRIDE_SCORE (75)` AND `m15_adx >= H1_VETO_OVERRIDE_ADX (40 default)`, with H4 not opposing
- **Shadow replay proof:** 20/20 SL_HIT, 0 TP_HIT across both BUY and SELL directions (commit `20e23a5`)
- **Status: Unchanged. Do NOT modify before commercial launch.**

---

## 4. Telegram Publishing

**Files:** `tools/signal_watcher_pro.sh` (lines 940–976), `tools/telegram_push.py`, `tools/lib/telegrambot.py`

- YELLOW tier (score 70–74): watchlist alert, no entry/SL/TP
- GREEN tier (score ≥75): full alert with entry, SL, TP; chart attempted via `tools/chart_generator.py`
- Cooldown state: `logs/state/last_sent_<PAIR>_<TF>.txt`
- Last confirmed live send: May 19 2026 (TELEGRAM_SEND=PASS in daily summary)
- **Status: ACTIVE**

---

## 5. Supabase / ProfitLab Publishing

**Files:** `tools/supabase_publish.py`, called from `tools/signal_watcher_pro.sh:966–972`

- Called after successful Telegram send when SUPABASE_SERVICE_KEY is present in environment
- Endpoint: Supabase project `ozgkeslgjqbqfewojnmr` (production instance)
- Supabase service key: local presence observed in `config/strategy.env` — **value not recorded here**
- Table: `signals`, fields: pair, direction, entry_price, stop_loss, take_profit, signal_strength (1–5 scale), status=ACTIVE, timeframe, min_tier, rationale
- Dedup: `has_active_signal()` checks for existing ACTIVE row per pair before insert
- min_tier mapping: YELLOW → `free`, GREEN → `pro`

**UNCONFIRMED:** No log evidence of a successful Supabase insert was found in this audit window.
The code path is wired and the key is present, but production insert success must be verified
against the next qualifying signal event.

---

## 6. Daily Summary

**Files:** `tools/daily_summary.sh`, `tools/daily_summary_server_gate.sh`

- Live cron: `10 * * * *` → `daily_summary_server_gate.sh`
- Target window: server-UTC hour 20
- Send dedup: `state/daily_summary_sent_<date>.ok`
- Last-good fallback: active (commit `26e333d`) — reads `logs/clock_drift_last_good.json`, estimates server UTC from last-known-good offset, valid up to 28800 seconds (8 hours)
- **Fallback scope: daily summary only. Trading gates (market_open.sh) are not affected.**

| Date | Result |
|------|--------|
| 2026-05-19 | PASS — sent at 20:16 UTC (`state/daily_summary_sent_2026-05-19.ok` present) |
| 2026-05-20 | MISSED — CLOCK_FAIL persisted through entire 20 UTC window |
| 2026-05-21 | MISSED — CLOCK_FAIL for most of day; clock recovered but window had passed |
| 2026-05-22 | PENDING at audit time — gate active, server UTC ~12:00, target 20:00 |

---

## 7. Clock Drift Observability

**Files:** `tools/clock_drift_check.py`, `tools/clock_drift_check.sh`
**Cron:** `55 * * * *`
**State:** `logs/clock_drift_status.json`, `logs/clock_drift_last_good.json`

At audit time:
- `drift_seconds = -14757` (~4.1 hours; device clock is ahead)
- `server_clock_ok = true`
- `local_clock_unsafe = true`
- `status = DRIFT_WARN`
- Sources confirmed: Google, OANDA, Yahoo, Cloudflare (4 sources, spread 3s)

---

## 8. Crontab State Note

**Important:** `state/bota_shipmode_crontab.txt` is **stale** relative to the live installed crontab.
It shows the old `daily_summary.sh` direct call at `59 23 * * *`.
The live crontab is the authoritative source; it correctly has `daily_summary_server_gate.sh` at `10 * * * *`.
Do not use `state/bota_shipmode_crontab.txt` to restore or rebuild the crontab without reviewing against `crontab -l`.

---

## 9. Unknowns / Not Proven

| Item | Status |
|------|--------|
| Supabase production insert success | **Unconfirmed** — no insert log in this audit window |
| USDJPY in active signal scan | **Not confirmed** — indicators cached, not in scan cron |
| ADX hard gate threshold | Not in `strategy.env`; default `adx < 20.0` lives in scoring logic only |
| May 21 daily summary | Missed — no `state/daily_summary_sent_2026-05-21.ok` |

---

## 10. Risks

| Risk | Severity |
|------|----------|
| Supabase insert unproven in production | Medium — must be verified on next live signal |
| `state/bota_shipmode_crontab.txt` stale — could cause restore errors | Low — document and do not use as restore source |
| Daily summary can miss if CLOCK_FAIL persists >8h through target window | Medium — last-good fallback helps but has age limit |
| `H1_VETO_OVERRIDE_SCORE` duplicate line in `strategy.env` (lines 25–26) | Low — both values are 75, no functional impact |
| Supabase publish block nesting in `signal_watcher_pro.sh:963–973` | Medium — Supabase call is inside Telegram cooldown block; brittle but currently correct |

---

## 11. Not Implemented (Pre-Commercial Constraints Confirmed)

- No TradingView webhook
- No pair expansion for signal scanning (USDJPY not in scan)
- No threshold changes
- No H1 veto changes
- No commercial product message layer

---

## 12. Next Branch

```
feat/signal-product-message-v1
```

Do not open this branch until this checkpoint commit has been reviewed.
