
## 2026-05-07T06:04:18Z — Bootlog: BotA ship-mode network/cache state

- Local timestamp: Thu May  7 16:04:18 AEST 2026
- UTC timestamp: Thu May  7 06:04:18 UTC 2026
- Watcher short SHA: ff1a040a835d
- Server-clock watcher patch: PRESENT
- Watcher syntax: PASS
- Code files replaced in this step: NO
- Strategy changed: NO
- Cache updated in this step: NO
- Runtime issue found: `crond` not running during audit.
- Cache issue found: M15 raw cache stuck at `2026-05-05T18:30:00Z`.
- Network nuance:
  - DNS resolution works in curl/Python.
  - TLS works.
  - Root provider endpoints may return HTTP 403/429.
  - Curl code 23 was likely caused by pipe/head truncation.
- Required next boot action:
  - Start crond.
  - Run manual updater.
  - Re-test watcher dry run.

## 2026-05-07T06:24:52Z — Bootlog: runtime validation after ship-clock patch

- Server-clock watcher patch: active and committed.
- Manual updater: PASS.
- Cache freshness: PASS.
- Watcher stale gate: PASS, no stale skip after fresh cache.
- Watcher reached scoring/filter: PASS.
- Strategy changed: NO.
- Remaining scheduler check: exact `crond` and `market_open.sh`.

## 2026-05-07T06:34:51Z — Bootlog: market_open.sh server-clock patch

- File replaced: `tools/market_open.sh`
- Reason: Android/device UTC drift during ship sea-day time changes.
- New behavior: uses HTTPS Date headers to compute server UTC.
- Fail behavior: Closed if server clock unavailable.
- Strategy changed: NO.

## 2026-05-08T22:35:26Z — Sea-day BotA health proof

- Crond: PASS.
- Market gate server UTC: PASS.
- Cache freshness: PASS.
- Watcher reached filter/scoring: PASS.
- Ship/Android time no longer controls critical trading gates.

---
## 2026-05-09 Boot/Session Log

| Item | Status |
|---|---|
| Clock drift fix v2.0.3 | ACTIVE |
| Market gate server clock | ACTIVE |
| Crond | RUNNING |
| Watcher reaches scoring | PASS |
| Post-Apr-14 accepted signals | 0 (explained) |
| Supabase stuck signal | CLOSED |
| GitHub Security Scan | PASS |
| Strategy thresholds | UNCHANGED |
| Next action | Shadow feeder for rejected candidates |

---
## 2026-05-09 — Rejected Shadow Tracker Installed

| Item | Status |
|---|---|
| `tools/rejected_shadow_tracker.py` | INSTALLED |
| Syntax check | PASS |
| Server-clock safety | ACTIVE |
| First useful live run | PASS |
| Rows replayed | 2 |
| Fetch errors | 0 |
| Outcomes | 2 x `SL_HIT` |
| Production changed | NO |
| Strategy changed | NO |
| Telegram changed | NO |
| Cron added | NO |

Notes:
- First invalid OANDA 400 output was archived because timestamps were future-dated versus OANDA server time.
- Cron intentionally not added yet. Need more proof from real non-future rejected candidates before automation.

---
## 2026-05-09T04:06:44Z — Shadow Tracker Final Success

| Item | Status |
|---|---|
| Commit | `71db50c` |
| Tracker installed | YES |
| GitHub pushed | YES |
| First useful replay | PASS |
| Rows replayed | 2 |
| Fetch errors | 0 |
| Outcomes | 2 x `SL_HIT` |
| Production changed | NO |
| Strategy changed | NO |
| Telegram changed | NO |
| Cron added | NO |

Next action: wait for non-future score >=65 H1-neutral/H1-veto rejected candidates before automating with cron.

---
## 2026-05-12 — Signal Fired

| Item | Status |
|---|---|
| First signal post-drought | EURUSD M15 BUY score=75.70 |
| Telegram delivery | CONFIRMED |
| H1 override | ACTIVE (score>=75) |
| Drought duration | 28 days (Apr 14 – May 12) |
| Root cause | Clock drift + weak market setup |
| Status | RESOLVED |

---
## 2026-05-12T01:04:58Z — First Signal After Drought

| Item | Status |
|---|---|
| First accepted signal after drought | EURUSD M15 BUY score=75.70 |
| Telegram delivery | CONFIRMED |
| Chart image delivery | CONFIRMED |
| H1 neutral override | ACTIVE |
| Entry | 1.17870 |
| SL | 1.17760 |
| TP | 1.18090 |
| Strategy changed | NO |
| Production changed | NO |
| Cron changed | NO |

Notes:
- This confirms BotA is no longer in a total no-send state.
- Do not change thresholds based on one signal.
- Continue monitoring server-clock availability and Twelve Data usage.

---
## 2026-05-12 — Telegram Logo Updated

| Item | Status |
|---|---|
| Toma Signal AI / BotA logo | ACCEPTED |
| Uploaded to Telegram | YES |
| Production code changed | NO |
| Strategy changed | NO |
| Cron changed | NO |

---
## 2026-05-14 — Shadow Tracker Fix + H1 Outcome Proof

| Item | Status |
|---|---|
| `filter_str` column mapping | FIXED |
| Syntax check | PASS |
| Shadow rows joined to alerts.csv | 10/10 matched |
| H1_trend_neutral rows | 8 |
| Resolved H1 outcomes | 5 SL_HIT / 0 TP_HIT |
| Pending H1 outcomes | 3 OPEN_PENDING |
| Current H1 verdict | Protective so far |
| Strategy thresholds | UNCHANGED |
| Production behavior | UNCHANGED |
| Telegram behavior | UNCHANGED |
| Cron behavior | UNCHANGED |
| Next action | Recheck pending rows after outcome window |

---
## 2026-05-14 — Shadow JSONL Dedup + Clean State

| Item | Status |
|---|---|
| JSONL dedup | DONE (13→10 rows) |
| Resolved | 7 (all SL_HIT) |
| Pending | 3 (resolve after May 14 16:00 UTC) |
| H1 veto verdict | PROTECTIVE — do not change |
| Next action | Rerun tracker after May 14 16:00 UTC |

---
## 2026-05-15 — Final H1 Replay Resolution

| Item | Status |
|---|---|
| May 13 pending rows | RESOLVED |
| May 13 outcomes | 3 SL_HIT / 0 TP_HIT |
| Clean JSONL state | 10 rows |
| All rejected sample | 10 SL_HIT / 0 TP_HIT |
| H1_trend_neutral sample | 8 SL_HIT / 0 TP_HIT |
| score_gate sample | 2 SL_HIT / 0 TP_HIT |
| H1 verdict | PROTECTIVE in current sample |
| Strategy thresholds | UNCHANGED |
| Production behavior | UNCHANGED |
| Telegram behavior | UNCHANGED |
| Cron behavior | UNCHANGED |

---
## 2026-05-19 — PR #4 Deployed

| Item | Status |
|---|---|
| clock_drift_check.py | INSTALLED |
| clock_drift_check.sh | INSTALLED |
| Cron hourly :55 | ADDED |
| market_open.sh | UNCHANGED |
| Strategy | UNCHANGED |
| Next | Telegram daily summary |

---
## 2026-05-19 — PR #4 Actual Deployment Confirmed

| Item | Status |
|---|---|
| Local merge to main | DONE |
| clock_drift_check.py | ON DISK |
| clock_drift_check.sh | ON DISK |
| Python syntax | PASS |
| Bash syntax | PASS |
| Live run | PASS |
| Live result | DRIFT_WARN |
| Drift | approx -7568s |
| Server clock | OK |
| Cron hourly :55 | ADDED |
| Strategy | UNCHANGED |
| H1 logic | UNCHANGED |
| Thresholds | UNCHANGED |
| Telegram logic | UNCHANGED |
| Production observability | CHANGED |
| Production trading behavior | UNCHANGED |
| Previous docs claim 2c9d8f3 | CORRECTED |
