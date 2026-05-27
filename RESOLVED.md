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
