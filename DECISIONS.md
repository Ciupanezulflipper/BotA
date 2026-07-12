# BotA Decisions Register

## Active Locked Decisions

### 2026-04-22 — Live watcher scope
- Decision: Keep live watcher scope at `EURUSD GBPUSD` on `M15`
- Status: LOCKED
- Why:
  - End-to-end recovery is proven for current live scope
  - USDJPY is technically validated, but not yet approved for live watcher scope
  - No infrastructure reason currently exists to widen live scope
- Not approved:
  - Adding `USDJPY` to live watcher
  - Lowering thresholds just to force alerts

### 2026-04-22 — Workflow standard
- Decision: Use evidence-driven workflow files as source of truth
- Status: LOCKED
- Required artifacts:
  - `CONTINUITY.md`
  - `state/STATE.json`
  - `DECISIONS.md`
  - `RESOLVED.md`
  - `tools/handoff_pack.sh`
- Rule:
  - No meaningful BotA fix is considered done until continuity + state + decision trail are updated

## signal_closer.py role — 2026-04-24
- Classification: manual guarded admin tool
- Not cron-managed (confirmed via crontab -l | grep closer = empty)
- Live execution requires: --live --confirm CLOSE_SIGNALS --max-batch N
- Bulk close requires: --allow-bulk
- Root cause of March 13: live default without guardrails — fixed in v2

## BotA git auth path — 2026-04-26
- Decision: BotA git auth path is SSH, not HTTPS+PAT
- Status: LOCKED
- Proven:
  - local SSH key authenticated successfully to GitHub
  - `git fetch origin` over SSH passed
  - `git push origin main` over SSH passed
  - BotA remote URL is `git@github.com:Ciupanezulflipper/BotA_Prod_2025_11.git`
- Consequence:
  - PAT is no longer required for normal BotA `git pull` / `git push`
- Do not change:
  - `origin` back to HTTPS unless there is a separately documented reason

## Gitleaks failure classification — 2026-04-26
- Decision: treat current Gitleaks failure as likely valid historical secret exposure until proven otherwise
- Status: LOCKED
- Proven:
  - custom OANDA rule is not matching env-var names
  - code-level OANDA hits are env reads/usages only
  - historical `.env` and `config/tele.env` were committed with secret-bearing fields
- Do not change:
  - do not loosen `.gitleaks.toml`
  - do not allowlist `.env` or `config/tele.env`
  - do not mark the Gitleaks failure as false positive

## Secret rotation scope — 2026-04-26
- Decision: do not rotate all credentials in this session
- Status: LOCKED
- Priority for any near-term rotation:
  - OANDA_API_TOKEN
  - SUPABASE_SERVICE_KEY
  - TELEGRAM_BOT_TOKEN
- Deferred:
  - lower-priority/read-only provider keys
- Do not change:
  - do not weaken .gitleaks.toml just to get green CI

## Product Market Pulse send gate — 2026-05-27
- Status: LOCKED
- Decisions:
  1. `--send` mode requires `--chat-id` to be passed explicitly on the command line at all times.
     Do not default to `TELEGRAM_CHAT_ID` env var for Step 5 or any early rollout phase.
  2. Market Pulse must not publish to ProfitLab/Supabase `signals` table.
     `supabase_published=false` is mandatory for all Market Pulse message types.
  3. Daily Market Pulse must go to private test chat first.
     Require 3 confirmed successful private daily sends before main channel or cron rollout.
  4. Main BotA channel rollout requires a separate explicit approval step.
     Do not widen send scope to the main channel without that approval.
  5. Cron scheduling for Market Pulse requires a separate explicit approval step after private proof.
     Do not add cron for any Market Pulse send without that approval.
- Proof:
  - Step 5 commit `274b0d3`, tag `step-5-private-send-confirmed-2026-05-27`
  - Step 6 commit `6aa985e`, tag `step-6-wrapper-gates-2026-05-27`
  - Step 6A layout commit `65d1137`
  - First private wrapper send: `LIVE_SEND_EXIT_CODE=0`, `telegram_sent=True`, `supabase_published=False`

---

## 2026-07-10 — Watcher decision journaling and delivery dedup

<!-- BOTA_OBSERVABILITY_V4_2026_07_10 -->

- [proven] Decision: `logs/alerts.csv` is the completed-decision journal and must be written before rejection or delivery exits.
- [proven] Decision: Telegram/Supabase delivery dedup must remain separate from decision journaling.
- [proven] Decision: `last_hash_<PAIR>_<TF>.txt` represents successful real Telegram delivery, not merely candidate evaluation.
- [proven] Decision: delivery-hash comparison is read-only before send; the hash is marked only after successful real Telegram delivery.
- [proven] Decision: preserve the existing seven-field hash identity for this repair.
- [proven] Decision: do not reset historical delivery hashes or cooldown files.
- [proven] Decision: do not modify strategy, H1 veto, ADX handling, thresholds, watched pairs/timeframe, RR rules, Telegram tiers, or cron cadence in this repair.
- [inferred] Separate Supabase-specific delivery retry state may be evaluated later, but it is outside this approved observability repair.

---

## 2026-07-12 — Heartbeat delivery and deadman state correction

<!-- BOTA_HEARTBEAT_OBSERVABILITY_CORRECTION_V32_2026_07_12 -->

- [proven] Decision: credential loading must use scoped `_load_telegram_creds()` — no `source`, no `set -a`, no other variable assigned or exported from `.env.runtime`.
- [proven] Decision: Telegram response validation must use a deterministic JSON parser confirming `ok is True` (boolean). String `"true"`, absent field, and boolean `false` are all rejected.
- [proven] Decision: missing shadow file and empty timestamp field are distinct evidence faults, each with their own marker, and neither is classified as `HEALTHY`.
- [proven] Decision: `deadman.flag` must only be created after confirmed Telegram delivery of the deadman alert.
- [proven] Decision: `deadman.flag` must only be removed after confirmed Telegram delivery of the recovery notice.
- [proven] Decision: delivery failure markers (`DEADMAN_DELIVERY_FAILED`, `RECOVERY_DELIVERY_FAILED`) are emitted and prior flag state is preserved unchanged.
- [proven] Decision: every HEARTBEAT_RESULT and DEADMAN_RESULT marker is emitted via `result()` to both stdout and `cron.heartbeat.log`.
- [proven] Decision: stale timestamp evidence faults (`INVALID_SHADOW_TIMESTAMP`, `FUTURE_SHADOW_TIMESTAMP`, `SHADOW_HEARTBEAT_MISSING`, `SHADOW_TIMESTAMP_MISSING`) do not mutate `deadman.flag`.
- [proven] Decision: the corrected heartbeat must not be deployed until documentation-and-state closure, a separate deployment plan, and explicit approval are complete.
- [proven] Decision: strategy, H1 veto, ADX gates, thresholds, pair scope, cron cadence, and Supabase/OANDA operations are out of scope for this correction.
