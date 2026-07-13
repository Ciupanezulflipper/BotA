# BotA Resolved Issues

## 2026-04-21 / 2026-04-22

### Yahoo 429 retry storm
- Status: RESOLVED
- Root cause:
  - Yahoo fallback could return 429 and updater retried generic non-zero exits
- Fix:
  - `tools/data_fetch_candles.sh` exits with code `3` on Yahoo 429
  - `tools/indicators_updater.sh` stops retrying on rc=3
- Proof:
  - syntax checks passed
  - fetch/build flow recovered

### phase=Unknown contract mismatch
- Status: RESOLVED
- Root cause:
  - `tools/market_open.sh` emitted descriptive strings
  - `tools/scoring_engine.sh` accepted only exact `Open` or `Closed`
- Fix:
  - `tools/market_open.sh` now emits exact `Open` or `Closed`
- Proof:
  - scorer moved from `phase=Unknown` to `market phase Closed`

### stale watcher lock regression
- Status: RESOLVED
- Root cause:
  - stale watcher lock blocked live watcher execution
- Fix:
  - stale lock detection/removal proven in watcher output
- Proof:
  - watcher resumed and executed `--once` runs successfully

## 2026-05-27

### Step 6 daily pulse wrapper implementation + first private live send
- Status: RESOLVED (wrapper and first send proven — cron rollout still open/not active)
- What was proven:
  - `tools/run_daily_pulse.sh` built with dedup gate and `--dry-run` support.
  - First private live send: `LIVE_SEND_EXIT_CODE=0`, `telegram_sent=True`, `supabase_published=False`.
  - Dedup file `state/daily_pulse_sent_2026-05-27.ok` created correctly.
  - Layout cleanup: heavy separator bars removed; mobile-friendly two-line-per-pair format confirmed.
  - `--dry-run` skips correctly when dedup file present.
- Step 6 commit: `6aa985e`, tag: `step-6-wrapper-gates-2026-05-27`
- Layout cleanup commit: `65d1137`
- Branch: `main`, pushed to `origin/main`.
- Cron: NOT active. Manual sends only at this stage.
- Main BotA channel: NOT approved.
- Remaining gate: 3 successful private daily sends before cron/main channel decision.
- Production trading behavior changed: NO.
- Strategy changed: NO.
- H1 logic changed: NO.
- Thresholds changed: NO.
- Supabase publish for Market Pulse: NO (remains false).
- ProfitLab executable signal behavior: UNCHANGED.

### Step 5 private Telegram Market Pulse send
- Status: RESOLVED
- What was proven:
  - `tools/product_message_v1.py --send --chat-id <TEST_CHAT_ID>` delivered message to private test chat.
  - `telegram_sent=True` confirmed in log and stdout.
  - `supabase_published=False` confirmed.
  - Shadow mode continues working: `telegram_sent=False`, `supabase_published=False`.
  - macro6=3 neutral/default no longer displayed as "macro filter active".
  - Market Pulse contains no entry, SL, or TP.
  - Market Pulse disclaimer present.
- Commit: `274b0d3`
- Tag: `step-5-private-send-confirmed-2026-05-27`
- Branch: `main`, pushed to `origin/main`.
- Production trading behavior changed: NO.
- Strategy changed: NO.
- H1 logic changed: NO.
- Thresholds changed: NO.
- Cron changed: NO.
- Supabase publish for Market Pulse: NO (remains false).
- ProfitLab executable signal behavior: UNCHANGED.

---

<!-- BOTA_SIGNAL_LIFECYCLE_V31_2026_07_14 -->

## 2026-07-14 — Signal Lifecycle v3.1 — Seven Root-Cause Defects

**Status: RESOLVED IN ISOLATED IMPLEMENTATION**
**Rollout status: NOT PUSHED / NOT MERGED / NOT DEPLOYED**
**Real production behavior: NOT YET PROVEN**
**Subscriber closure notification: NOT IMPLEMENTED**

### Root causes

1. Signal expiry used wall-clock elapsed hours. Weekend gaps and closed-market periods counted incorrectly toward the holding period.
2. TP/SL evaluation was deferred until the market-time threshold. Signals that reached TP or SL before threshold were not closed; they waited until expiry and were then cancelled as unresolved instead of being closed WIN/LOSS.
3. Same-M15-candle ambiguity applied a TP-first rule. When both TP and SL were touched in the same M15 candle, the closer reported WIN. The SL may have been the actual first touch, making the result optimistic.
4. M15 cache coverage logic could reject a valid historical cache. A cache that started before `effective_start` but contained a candle whose range spanned `effective_start` was incorrectly rejected.
5. `created_at` microseconds were truncated via `int(created.timestamp())` before the S5 boundary calculation, shifting the effective entry boundary to the wrong second.
6. Exact threshold-minus-five-second S5 data was required. Real OANDA S5 data is sparse; the closer returned `DATA_UNAVAILABLE` when the last available S5 candle was a few seconds earlier than exactly `threshold - 5`.
7. A partial-entry signal at an exact M15 threshold boundary unconditionally required S5 data (`need_s5=True` when `is_partial_start=True`) and returned `DATA_UNAVAILABLE` even when the whole-candle M15 H/L proved no boundary touch. The full-candle OHLC subsumes any sub-period H/L, making S5 unnecessary in this case. Found by adversarial test F-35.

### Fixes

1. Replaced wall-clock age check with `compute_threshold()` counting completed M15 candles (900s each). Weekend gaps excluded. Normal threshold: 96 candles / 24 market hours.
2. `resolve_signal_outcome` is now called on every closer run. TP/SL hits before threshold are detected and returned; `prepare_signal_action` only returns `None` (leave ACTIVE) on clean `OPEN`.
3. Same-S5 ambiguity now resolves as `LOSS` with reason `AMBIGUOUS_S5_STOP_FIRST`. Optimistic TP-first rule removed.
4. Coverage check fixed: accepts any cache where at least one candle satisfies `int(c["t"]) <= effective_start_epoch < int(c["t"]) + tf_sec`.
5. `ceil_to_s5_from_datetime(dt)` uses microsecond-accurate integer arithmetic: `total_us = days*86400*1_000_000 + seconds*1_000_000 + microseconds`. No truncation.
6. S5 lookback extended one M15 period back for partial-start candles. `valid_exit` filter accepts any S5 where `t + 5 <= threshold`. Sparse coverage accepted when structurally valid.
7. Early TIME_EXIT path added: when `is_threshold_at_m15_boundary=True` and `not m15_touches_any_boundary(...)`, return M15 close directly regardless of `is_partial_start`.

### Regression-test proof

- `tests/test_signal_closer_lifecycle.py`
- 119 tests, 0 failures, 0 errors
- PYTHONHASHSEED 0 / 1 / 17 / 99991 — all EXIT=0
- `python3 -m py_compile tools/signal_closer.py` — PASS
- `bash -n tools/run_signal_closer_live.sh` — PASS
- `git diff --check` — PASS

### Commit

`be8c6efc8eab43c3e9b99c995787a825d3c3b8f5` on branch `fix/signal-lifecycle-market-hours-20260713`

Changed files:
- `tools/signal_closer.py`
- `tools/run_signal_closer_live.sh`
- `tests/test_signal_closer_lifecycle.py`

### What is NOT yet resolved

- Branch push to origin: NOT done
- Draft PR: NOT opened
- CI: NOT run
- Read-only dry-run on live BotA: NOT done
- Production deployment: NOT done
- Real-signal proof: NOT done
- Telegram closure notification: NOT implemented

Do not label the rollout as resolved until all remaining gates are completed and recorded.

---

## 2026-07-10 — Watcher pre-journal dedup observability defect

<!-- BOTA_OBSERVABILITY_V4_2026_07_10 -->

- Status: RESOLVED
- [proven] Root cause: content dedup executed before `alerts.csv` journaling and wrote hash state before confirmed Telegram delivery.
- [proven] Fix: journal every completed parsed decision before rejection and Telegram delivery gates.
- [proven] Fix: split delivery hash calculation, read-only comparison, and post-success marking.
- [proven] Fix: update delivery hash only after successful real Telegram send.
- [proven] Static validation: PASS.
- [proven] Atomic deployment: PASS.
- [proven] Natural cron-cycle validation: PASS.
- [proven] Natural proof wrote two rejected HOLD rows while preserving both delivery hashes and both `last_sent` files.
- [proven] Installed watcher SHA-256: `b8a3adf46582e3a69d5b22d12a4da070bc8be2ceff76a4aa99e9d6c96544a9ef`.
- [proven] Strategy and production selection rules changed: NO.
- [not proven] Whether any valid signal was missed during the historical June outage remains unresolved.
