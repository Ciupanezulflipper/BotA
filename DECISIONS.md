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

<!-- BOTA_SIGNAL_LIFECYCLE_V31_2026_07_14 -->

## 2026-07-14 — Signal Lifecycle Contract (LOCKED)

**Scope:** `tools/signal_closer.py`, `tools/run_signal_closer_live.sh`, `tests/test_signal_closer_lifecycle.py`
**Implementation commit:** `be8c6ef` on branch `fix/signal-lifecycle-market-hours-20260713`
**Status: LOCKED**

### Lifecycle evaluation contract

- Always evaluate TP and SL on every closer run, regardless of whether the market-time threshold has been reached.
- Measure normal maximum hold using completed market candles, not elapsed wall-clock hours.
- Current normal threshold: 24 market hours = 96 completed M15 candles (900s each). Weekend gaps are excluded. Do NOT revert to wall-clock normal expiry.
- Compute effective entry boundary as `ceil_to_s5_from_datetime(created_at)` using microsecond-accurate arithmetic. Do NOT use `int(created.timestamp())`.
- Exclude all price action before `effective_start_epoch` from TP/SL evaluation.
- Use OANDA S5 candles to refine a boundary touch to 5-second resolution when M15 H/L indicates a touch.
- When the same S5 candle touches both TP and SL, resolve conservatively as LOSS with reason `AMBIGUOUS_S5_STOP_FIRST`. Do NOT restore the old TP-first same-candle rule.
- Sparse S5 data is valid evidence when structurally trustworthy. Do NOT require exact threshold-minus-5s coverage.
- When `is_threshold_at_m15_boundary=True` and M15 H/L shows no touch, the M15 close is authoritative even for partial-start candles. S5 is not required in this case.
- Never use post-threshold candles for TP, SL, or TIME_EXIT pricing. Do NOT scan post-threshold data.
- Normal expiry with trusted evidence → `CLOSED` outcome `TIME_EXIT`. `closed_at` = `threshold_epoch`.
- `CANCELLED` is reserved for `DATA_UNAVAILABLE` cases that reach `hard_max_age` (currently 168h). Do NOT cancel a clean `OPEN` state merely because wall-clock hard age was exceeded.
- TP/SL `closed_at` = end of the first proving S5 candle (candle `t + 5`).
- Emergency unresolved cancellation uses trusted server time from HTTPS Date headers, never local Android time.

### Schema constraint

- Current live DB schema stores `status`, `result_pips`, `closed_at`.
- Exit price and close reason are logged in `logs/cron.closer.log` only.
- Do not add `exit_price`, `close_reason`, or other new columns without a separately approved schema migration that is coordinated with ProfitLab.

### Rollout constraint

- Do NOT deploy the lifecycle change without: draft PR, CI pass, read-only dry-run validation on live BotA, and explicit production approval.
- Do NOT merge or push directly to `main`.
- Do NOT mark this as deployed until first real-signal proof is recorded.

### Telegram closure notifications

- Telegram closure notifications are NOT implemented in this change.
- The subscriber workflow (ACTIVE → CLOSED → subscriber notified) remains incomplete.
- Do NOT claim subscriber closure notification is working until it is separately implemented and proven.

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

<!-- BOTA_DEEPSOURCE_GOVERNANCE_2026_07_16 -->

## 2026-07-16 — DeepSource Documentation Coverage Governance (LOCKED)

**Scope:** PR #7 (`fix/signal-lifecycle-market-hours-20260713`), `tools/signal_closer.py`, `tools/signal_resolution.py`
**Status: LOCKED**

### Evidence

- `tools/signal_closer.py`: 26/26 application callables documented — 100%
- `tools/signal_resolution.py`: 21/21 application callables documented — 100%
- PR-introduced application callables total: 47/47 — 100%
- Repository-wide application callables: 678 total, 174 documented — ~25.7%
- Pre-existing undocumented application callables: ~504 (outside PR #7 scope)
- DeepSource comparison/baseline value at time of analysis: 44.9%
- Main-branch DeepSource documentation coverage at PR open: ~18.6%
- AST audit tool: `ast.walk` over `FunctionDef`, `AsyncFunctionDef`, `ClassDef`; docstring = first node is `Expr(Constant(str))`
- No suppression annotations (`noqa`, `skipcq`, `type: ignore`, `nosec`) were added
- No filler or placeholder docstrings were used

### Why 44.9% cannot be satisfied within PR #7 scope

- The 44.9% comparison is a dynamic baseline computed by DeepSource, not a static configured threshold
- The baseline reflects repository-wide documentation density across all ~678 application callables
- PR #7 introduces 47 of those callables; documenting the other ~631 is outside PR scope
- Documenting unrelated legacy callables in PR #7 would create excessive review scope and regression risk
- No `.deepsource.toml` existed in the repository; DeepSource was configured entirely via dashboard

### Decision

- PRs must document all newly introduced or materially changed application callables: ENFORCED
- Pre-existing repository documentation debt must not block scoped PRs: AGREED
- Repository-wide documentation improvement is tracked separately in a dedicated GitHub issue
- Setting suppressions to pass DeepSource is prohibited
- Adding filler documentation to unrelated legacy callables in PR #7 is prohibited

### Required governance correction (repository-owner action)

DeepSource quality gate thresholds are configured at:
`https://app.deepsource.com/gh/Ciupanezulflipper/BotA/settings/`
Navigate to: Repository Settings → Quality Gates → Python → Documentation Coverage

**Recommended threshold:** 18% (grounded in measured main-branch coverage of ~18.6%)

**Progressive improvement targets (tracked in documentation-debt issue):**
- Phase 1: 20% (near-term, no new effort required — PR #7 alone achieves this)
- Phase 2: 25% (document highest-traffic production modules)
- Phase 3: 30%
- Phase 4: 35%
- Phase 5: 40%
- Phase 6: 45%

### What NOT to do

- Do not disable the Python analyzer
- Do not disable all metric enforcement
- Do not add suppression annotations to pass the check
- Do not set the threshold arbitrarily without grounding in measured coverage
- Do not document unrelated legacy callables inside PR #7
