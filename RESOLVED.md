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

---

## 2026-07-12 — Heartbeat delivery and deadman state correction (v3.2)

<!-- BOTA_HEARTBEAT_OBSERVABILITY_CORRECTION_V32_2026_07_12 -->

- Status: IMPLEMENTATION COMPLETE — deployment blocked pending plan and approval
- [proven] Branch: `fix/heartbeat-observability-20260712`, base `fa289ad`
- [proven] Implementation commit: `6cdfc7f97090b4bfae9ba0b015940205778d9ed6`
- [proven] Root cause: heartbeat used `grep`-based JSON check, leaked env via unsanitised source, classified missing evidence as HEALTHY, and mutated `deadman.flag` before confirmed delivery.
- [proven] Fix: scoped credential loader, `python3 json.load()` boolean validation, distinct missing-evidence markers, confirmed-delivery-only flag gating.
- [proven] Fix: all HEARTBEAT_RESULT and DEADMAN_RESULT markers written via `result()` to both stdout and log.
- [proven] Offline validation: 29 test cases, 108 assertions, 108 passed, 0 failed, 0 real network attempts.
- [proven] Secret-safety scans passed.
- [proven] CI Security Scan: completed/success on commit `6cdfc7f`.
- [proven] `tools/heartbeat.sh` SHA-256: `8226a935c30be8a3484ed20bf3e79192d9fb020f6dc827e4e89af3c23a2fe202`
- [proven] `tests/test_heartbeat.sh` SHA-256: `cad581f326ef5b4fbf7c1f26065cb43de3abc70cf9b4a573d7ff5bc4647e81c1`
- [proven] Production checkout unchanged. Historical-replay worktree unchanged. No live Telegram test run.
- [proven] Strategy, H1 veto, ADX gates, thresholds, pair scope, cron cadence, OANDA, Supabase: unchanged.
- [not proven] Live Telegram delivery behaviour of the corrected heartbeat — no production deployment has occurred.
- Deployment gate: requires separate plan, explicit approval, post-deployment verification.
