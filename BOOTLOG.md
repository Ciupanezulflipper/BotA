
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

---
## 2026-07-08 — Runtime crontab wipe checkpoint

### Incident

BotA was not unlucky or weak; it was unscheduled.

The live Termux crontab had lost the BotA runtime jobs and retained only:

- Dividend Capture Scanner block.
- BotA Daily Proof block, restored separately on 2026-07-05.

Missing jobs:

- watcher
- indicators updater
- shadow manager
- signal closer
- supervisor
- clock drift checker

Frozen evidence:

- `logs/cron.signals.log` frozen around 2026-06-22.
- `logs/cron.indicators.log` frozen around 2026-06-22.
- `logs/cron.closer.log` frozen around 2026-06-22.
- `logs/api_credits.json` frozen around 2026-06-22.

### Restore checkpoint

C1C restored and cleaned crontab.

Required counts passed:

- dividend scanner: 1
- watcher: 1
- updater: 1
- shadow: 1
- closer: 1
- daily proof: 1
- clock drift: 1
- supervisor: 1

Tracked code files changed: NO.

### C2 liveness checkpoint

Input metadata:

- `INPUT_TIMESTAMP_LOCAL=2026-07-08 14:45:51 CEST`
- `INPUT_TIMESTAMP_UTC=2026-07-08 12:45:51 UTC`
- `SOURCE=Termux`
- `SCOPE=BotA`

C2: PASS.

Verified:

- `crond` running with PID `8633`.
- Required BotA crontab line counts all equal `1`.
- Fresh runtime ages:
  - watcher: 0 min
  - updater: 2 min
  - closer: 0 min
  - shadow: 0 min
  - supervisor: 0 min
  - `api_credits.json`: 2 min
  - `state/runtime_health.json`: 0 min
- Watcher reached live scan and rejected/skipped by signal gates, not runtime failure.
- Updater fetched and built all configured pairs/timeframes with `fetch_fail_count=0 build_fail_count=0`.
- Closer ran live and found `0 ACTIVE` signals.
- Shadow manager ran and found `0 active signals`.
- Supervisor reported `HEALTHY` and wrote `runtime_health.json`.
- API credits moved to `used=60` for 2026-07-08.

### Phase 2 canonical crontab checkpoint

Input metadata:

- `INPUT_TIMESTAMP_LOCAL=2026-07-08 15:20:17 CEST` for commit/push.
- `INPUT_TIMESTAMP_UTC=2026-07-08 13:20:17 UTC` for commit/push.
- `INPUT_TIMESTAMP_LOCAL=2026-07-08 15:25:21 CEST` for restore drill.
- `INPUT_TIMESTAMP_UTC=2026-07-08 13:25:21 UTC` for restore drill.
- `SOURCE=Termux`
- `SCOPE=BotA`

Phase 2: PASS.

Committed and pushed:

- `e58844f ops: add canonical BotA crontab verification`

Files:

- `docs/BOTA_CANONICAL_CRONTAB.md`
- `ops/bota_crontab.canonical`
- `tools/install_canonical_crontab.sh`
- `tools/verify_canonical_crontab.sh`

Restore drill verified:

- backup created at `logs/crontab.backup.before_canonical_install_20260708_132521.txt`
- installer preserved Dividend Capture Scanner block
- installer preserved Dividend Capture Scanner `CRON_TZ=America/New_York`
- installer installed BotA canonical block with `CRON_TZ=UTC`
- `INSTALL_RC=0`
- all required counts equal `1`
- `BOTA_BLOCK_HASH_MATCH=YES`
- `PHASE2_VERIFY_PASS=YES`

### Status

C1C: PASS.

C2 liveness: PASS.

Phase 2 canonical crontab: PASS.

Current reliability score: 72/100.

### Required next boot/reliability work

- Verify Termux:Boot.
- Verify wake lock.
- Upgrade Daily Proof to report component freshness. CLOSED by commit `5744802`.
- Push runtime health to Supabase.
- Add ProfitLab Admin Health Panel.

### Phase 4C Daily Proof truth upgrade checkpoint

Timestamp: 2026-07-08 15:44:34 UTC

Result: PASS.

Commit:
- `5744802` — `tools: strengthen BotA daily proof runtime reporting`

Verified:
- Daily Proof no longer only proves `crond` exists.
- It reports runtime status, supervisor freshness, watcher/updater/closer/shadow freshness, canonical crontab verification, hash match, and reasons.
- Final dry-run after rebase showed `Runtime: HEALTHY`, `Canonical crontab: PASS`, `Hash match: YES`, and `Reasons: none`.
- Push succeeded to `origin/main`.
- No force push used.

Still open after Phase 4C:
- Real reboot recovery proof.
- Supabase runtime health push.
- ProfitLab Admin Health panel.

Current reliability score: 72/100.

<!-- PHASE5_RUNTIME_HEALTH_PUSH_CLOSURE_20260708 -->
## 2026-07-08 — Phase 5 Runtime Health Push Closure

Phase 5 runtime health push was verified end-to-end.

Evidence:

- Migration created `public.bot_runtime_health`.
- Edge Function `bot-health-ingest` deployed with `verify_jwt = false` and protected by limited header secret.
- No Supabase service-role key stored on Termux.
- Manual Python sender push returned HTTP 200.
- Wrapper real push returned HTTP 200.
- Canonical crontab updated and installed.
- Cron-fire proof passed: runtime-health push executed from cron and updated Supabase.
- Canonical hash match after cron install: PASS.
- Core BotA cron jobs preserved exactly once.

Result: Phase 5 runtime-health push is functionally closed.
