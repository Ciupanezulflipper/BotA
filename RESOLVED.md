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

## Resolved — 2026-07-11 Historical Replay Runtime Safeguards

- [proven] Resolved: scheduler process detection false negative; `crond` PID `5027` and advancing scheduled logs proved scheduler execution.
- [proven] Resolved: runtime-health delivery false positive; fresh authoritative logs showed HTTP `200` and `RESULT=PASS rc=0`.
- [proven] Resolved: heartbeat environment-path root cause; `config/tele.env` was absent while `.env.runtime` contained the required Telegram variable names.
- [proven] Resolved: audit-branch heartbeat implementation now sources `.env.runtime` and fails closed when unavailable.
- [proven] Resolved: local operability validation now uses the actual `combine_runtime_and_freshness` API.
- [proven] Resolved: GitHub Actions passed for audit commit `43b2ddf16d5aaed7be6d1d7366ecfb4c37b77957`.
- [not proven] Unresolved: Android device clock correction.
- [not proven] Unresolved: production heartbeat deployment.
- [not proven] Unresolved: live Telegram heartbeat delivery after deployment.
- [not proven] Unresolved: full historical data integrity and complete replay parity.

## Resolved — 2026-07-11 External Audit Closure

- [proven] Resolved: external-audit phase is formally closed.
- [proven] Resolved: Audit 2 (Claude Fable 5) identified and documented the heartbeat deadman removal, missing Telegram response validation, environment-scope leak, and missing behavioral CI coverage as critical findings. These are accepted and entered into the correction backlog.
- [proven] Resolved: Audits 1, 3, 4, and 5 did not have repository access; their contributions were limited to logic-level checks, retractions, or limitation disclosure.
- [proven] Resolved: PR #6 is classified as mixed scope. Merge requires heartbeat correction backlog items 1–4 complete.
- [proven] Resolved: UNKNOWN quiet-interval coverage is 770/1560 = 49.36% of nominal M15 cycles per pair. This is evidentiary silence, not proven downtime.
- [proven] Resolved: a single 7,267-second device-clock correction is invalid; drift varied over the window.
- [proven] Resolved: per-boundary true-UTC placement is not proven. Device-log timestamps must not be treated as verified UTC without per-date drift bounds.
- [proven] Resolved: `state/STATE.json` deadman-installed claim is contradicted by the audit-head heartbeat. This contradiction is in the correction backlog (item 6).
- [proven] Resolved: Q2 and Q3 are accepted as material missing intervals in the epoch summary. Adding them is correction backlog item 7.
- [not proven] Unresolved: heartbeat deadman restoration (correction backlog item 1).
- [not proven] Unresolved: Telegram `"ok":true` strict validation (correction backlog item 2).
- [not proven] Unresolved: environment-scope narrowing (correction backlog item 3).
- [not proven] Unresolved: deterministic offline heartbeat tests (correction backlog item 4).
- [not proven] Unresolved: PR #6 scope split or explicit mixed-scope classification (correction backlog item 5).
- [not proven] Unresolved: Q2/Q3 canonical epoch entries (correction backlog item 7).
- [not proven] Unresolved: exact per-boundary true-UTC using per-date drift bounds (correction backlog item 8–9).
- [not proven] Unresolved: CI re-run after correction backlog items 1–5 (correction backlog item 10).
