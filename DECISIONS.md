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
  3. Main BotA channel rollout requires a separate explicit approval step.
     Do not widen send scope to the main channel without that approval.
  4. Cron scheduling for Market Pulse requires a separate explicit approval step.
     Do not add cron for any Market Pulse send without that approval.
- Proof:
  - Commit `274b0d3`, tag `step-5-private-send-confirmed-2026-05-27`
  - Manual private test: `telegram_sent=True`, `supabase_published=False`
