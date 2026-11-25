# BotA Chat Handoff

Last updated: **2026-11-25 UTC**

Read first in a new AI session. Continue from the outstanding gate, not the old secret-rotation workflow.

Canonical detailed state and evidence: [CONTINUITY_CURRENT.md](CONTINUITY_CURRENT.md). Historical pre-rotation instructions are superseded.

## Current status

```text
BOTA_EDGE_STATUS=UNVALIDATED
LIVE_MONEY_TRADING=NO
PRIMARY_RUNTIME=HETZNER
DEPLOYED_RELEASE=83fa71e651483c95096ce635b525cacbf91cbc5d
PROVIDER=YAHOO
PAIRS=EURUSD,GBPUSD,USDJPY
TIMEFRAME=M15
LEGACY_ANDROID_RUNTIME=STOPPED
PHONE_REBOOT_TEST=PASS
SUPABASE_ROTATION=COMPLETE
HETZNER_DEDICATED_KEY=bota_hetzner
OLD_SHARED_KEY=bota_service
OLD_SHARED_KEY_REVOKED=YES
OLD_KEY_REJECTION_TEST=PASS
OVERNIGHT_PRODUCTION_STABILITY=PASS
CLEAN_SIGNAL_LIFECYCLE=PENDING
TELEGRAM_ROTATION=PENDING
TELEGRAM_ROTATION_AUTHORIZED=YES_2026-11-28_PLAN_REQUIRED
TELEGRAM_RECONCILIATION=PENDING
CREDENTIAL_BACKUP_CLEANUP=PASS
LEGACY_RETIREMENT_COMPLETE=NO
CLEAN_72H_WINDOW=OPEN_T0_APPROVED
CLEAN_72H_T0=2026-11-24T20:00:01.036Z
CLEAN_72H_EARLIEST_END=2026-11-27T20:00:01.036Z
PHONE_OANDA_ENDPOINT=REPORTED_PRACTICE
PHONE_OANDA_TOKEN_CLEANUP=LOW_PRIORITY
PHONE_REMAINING_API_KEYS=PENDING_REVIEW
REPAIR_BRANCH=CANDIDATE_D1_FRESHNESS_LOCAL_EXPOSURE_GUARD
RECENT_LEDGER_PROVENANCE=CROSS_CONTAMINATED
D1_REPAIR_DEPLOYED=NO
ONE_ACTIVE_PAIR_DIRECTION_CONTROL_DEPLOYED=NO
POLICY_B_ACCEPTED=195
PRE_REGISTERED_KILL_THRESHOLD=400
HISTORICAL_CORPUS_GATE=FAIL
STRATEGY_EDGE_VALIDATED=NO
STRATEGY_TUNING=NO
PRODUCTION_CHANGE_AUTHORIZED=NO_EXCEPT_APPROVED_2026-11-28_TELEGRAM_ROTATION_AFTER_PLAN
NEXT_ACTION=COMPLETE_TELEGRAM_FINGERPRINT_COMPARISON
FOUNDER_APPROVAL_REQUIRED=YES_FOR_MERGE_OR_DEPLOY
```

## Accepted evidence — do not repeat

- Legacy phone was a real producer sharing Hetzner's old Supabase key. Watchdog and runit stopped, launcher disabled, fresh-session and reboot persistence checks passed.
- Dedicated modern secret installed atomically at 19:27:30 UTC on 24 Nov without restart; other credentials preserved. Exact dashboard match established old key identity.
- New key authenticated at 19:28:44 UTC; scheduled closer reads 19:30 and 19:45 HTTP 200. Claude Code reported all relevant jobs succeeded and no credential override files existed. Successful job exits are not proof of writes.
- Old key revoked; deliberate rejection 19:59:56 HTTP 401 independently logged, new key read 20:00:01 HTTP 200.
- Overnight 24 Nov 20:39–25 Nov 10:18 UTC: 55/55 Hetzner reads, 164/164 health writes, zero legacy key requests and unexpected producers. No actual signal creation/closure in that window.
- ProfitLab privileged Edge Functions use separate legacy service-role path; health requests use a separate credential. Full billing transaction testing not performed.

## Remaining gates

1. Credential backup cleanup: PASS. Founder-approved exact rollback file deletion verified; active credentials unchanged. Never restore revoked key.
2. Telegram token rotation: approved for Saturday 28 Nov during FX closure, plan required before execution. Inventory Hetzner, Supabase send-telegram, phone and dividend scanner.
3. Natural signal lifecycle: pending real Hetzner creation and closure; never manufacture signals.
4. Telegram reconciliation: separate pending gate against Hetzner send records.
5. Overall retirement not complete. No merge or deploy approved; only the separately authorized Saturday Telegram rotation after its plan.

## Strategy and provenance

11 Nov EURUSD winner +20.8 pips legacy-created; 12 Nov GBPUSD cancellation legacy-performed; 23 Nov six overlapping Hetzner USDJPY BUY losses total -131.6 pips. Historical ledger mixed, not strategy-validation evidence. D1 writer/reader path mismatch falls back to ANY; future mutable-root fail-closed fix not deployed. Candidate one ACTIVE per pair+direction approved for isolated branch implementation; merge/deployment not authorized; requires historical replay counting removed winners and losses. Yahoo provider unchanged; local quota warnings not evidence of Twelve Data billing. Preserve all strategy boundaries. Do not tune or repair code during retirement.

## 25 Nov — observation boundary, residual hazards and tests-only branch

### 72-hour clean-producer acceptance

VERIFIED: founder reported deletion of bota_service; exact dashboard deletion time UNKNOWN. One deliberate GET /rest/v1/signals from bota-r5-01 (2.29.4.127) using revoked key returned HTTP 401 at terminal UTC 2026-11-24T19:59:56.371343Z; independent Edge record 19:59:56.410Z. The next new-key GET returned HTTP 200 at 20:00:01.036Z. No repeat rejection call necessary. Formal pre-registered T0 not evidenced. FOUNDER APPROVED T0: 2026-11-24T20:00:01.036Z; earliest 72-hour end 2026-11-27T20:00:01.036Z (22:00:01 Romania). Keep window open until one real Hetzner signal is created and closed with verified provenance; never fabricate a signal. Unexpected producer activity blocks acceptance and requires investigation and a new clean boundary. Latest accepted overnight evidence ends 2026-11-25T10:18:00Z: 55/55 DB reads, 164/164 health reports, zero legacy requests and unexpected producers. Window is NOT passed.

REPORTED phone reboot persistence PASS. Airplane mode during reboot UNKNOWN; absence of phone Telegram calls UNKNOWN. Supabase logs cannot prove absence of Telegram traffic. Do not repeat completed reboot or key tests to fill the historical gap.

### Residual credential gates

- Telegram token rotation and reconciliation remain separate pending gates. Founder approved rotation on Saturday 28 Nov during FX closure; send plan before execution. Inventory consumers and verify identity without exposing tokens.
- Obsolete rollback backup: PASS. Exact founder-approved deletion via root SSH; PASS: Backup removed; active credentials unchanged. No other production change.
- Phone remaining API keys: pending review. Founder REPORTED api-fxpractice.oanda.com in both phone files (.env and .env.runtime); practice endpoint, no live-money endpoint identified. Phone OANDA token cleanup is low priority; other keys still require review. No trading API calls.

### Lessons and deployment hazard

REPORTED historical cause of 6 Sep failed retirement: two startup paths (boot script and $PREFIX/etc/profile.d/start-services.sh); only one was disabled. Future retirement checklist must cover both boot and shell/profile startup, then persistence proof. Do not restart or repeat completed tests now.

VERIFIED deployed run_signal_closer_live.sh exports values from config/strategy.env, .env and .env.runtime, potentially overwriting inherited credentials. be_shadow_manager.py loads .env.runtime, .env, config/strategy.env and strategy.env using os.environ.setdefault, so it fills missing values rather than overwriting an existing environment variable. Other legacy readers remain a risk. REPORTED from prior Claude server check: none of those files existed in the deployed release. Implemented on isolated branch (not deployed): before staging/activation, fail the candidate release if any of .env, .env.runtime, config/strategy.env, strategy.env exists or is a symlink (including broken symlinks); keep credentials external, report offending paths only, never contents. Focused offline guard and deployment regressions passed; merge/deploy not approved.

### Founder-approved branch implementation

Branch [fix/retirement-d1-active-signal-tests-20261125](https://github.com/Ciupanezulflipper/BotA/tree/fix/retirement-d1-active-signal-tests-20261125). Baseline tests commit 762f942ecb6af45a13e83230bfd36ab93601219a; pushed partial implementation cd25a46c8ff36239f3bce8686b0f030478272939. Isolated laptop WSL worktree /home/tomag/BotA-retirement-tests-20261125. D1 mutable-root fail-closed reader and explicit DEGRADED health payload/reason implemented. Release guard rejects .env, .env.runtime, config/strategy.env and strategy.env (including dangling symlinks) on staging and finalized candidate validation. Offline focused results: D1 decision 3/3; guard and D1 health/recovery 3/3 (including four forbidden-file subcases); runtime-health regression 33/33; deployment regression 37/37. Shell syntax and git diff checks passed. No production deployment or runtime changes. At cd25a46 the exposure admission repair was not implemented; the candidate update below supersedes that state. The old direct-publisher distinct-same-direction acceptance is superseded at the strategy admission boundary, not by weakening exact retry deduplication. The founder subsequently approved local pair/direction records as the sole admission authority. No delivery-state ledger or live database query at admission. See candidate update below. Require integration and independent-delivery tests; do not merge or deploy. Historical replay must count removed winners/losses.

Both repairs deployed = NEW strategy generation. Evaluation starts at the later of (both repairs deployed) and (72-hour clean-producer acceptance passed, including any extension). No deployment, strategy evaluation or live-money trading authorized.

Stale documentation PRs BotA #139 and obsidian-engineering-knowledge #90 closed without merge on founder instruction; comments point to canonical records.

## Exactly one next action

Complete the two outstanding Telegram fingerprint comparisons before Saturday rotation. Separately review the isolated candidate and reconcile pre-existing ACTIVE rows/backlog before any deployment. Do not repeat completed audits, rotate keys before the approved window, merge, deploy, restart services, fabricate signals, or start strategy evaluation. Founder approval is not required for this isolated branch work. Keep natural lifecycle observation open under the approved extension rule.

## Branch review update - 25 November 2026

Founder accepted the D1 mutable-root fail-closed reader, visible DEGRADED health and release credential-file guard, subject to the pre-registered 36-hour freshness requirement. Missing, unparseable or stale updated_at is UNAVAILABLE/stale, including health reason d1_cache:<PAIR>:stale. Exposure admission is a durable local pair+direction record before accepted CSV/Telegram, with a UUID assigned at admission and propagated to both Supabase publication paths. Only the confirmed CLOSED/CANCELLED row with the matching signal ID and scope releases its record; changed SL/TP does not invalidate the ID match. Normal expiry 24h with usable candle coverage for orphan records; hard expiry 168h. A late retry for a replaced/expired admission cannot insert an old ACTIVE row; the sink checks its admission ID, not delivery status, and exact retries dedup by ID even after closure. Admission does not query Supabase ACTIVE rows or delivery state; each sink retains its independent retry behavior. This is isolated candidate code, NOT a production rollout. Merge/deploy remain unauthorized. Pre-activation must reconcile pre-existing ACTIVE rows and outstanding pre-generation delivery retries with the new local record boundary; late-retry rejection is covered by offline tests. Hard expiry is a local safety release, not proof a remote row closed during an outage.

Telegram plan Step 1: SHA-256(raw token), first 12 hex only. Founder REPORTED phone BotA token fingerprint 7e18d1067664 and dividend-capture-scanner token fingerprint 4adf3e925f93 (different from phone BotA). Founder REPORTED OANDA practice endpoint in both phone files; OANDA token cleanup low priority. Hetzner BotA token fingerprint UNKNOWN: automated SSH fingerprint request blocked by tool safety check; no bypass attempted. Supabase send-telegram token fingerprint UNKNOWN: connector has no secret-digest list; compare the existing project secret digest without retrieving raw value. Deployed send-telegram v38 reads TELEGRAM_BOT_TOKEN and TELEGRAM_ADMIN_CHAT_ID; known callers are ProfitLab Account.tsx admin test action and deployed stripe-webhook v48 (new subscription, active update/renewal, cancellation/inactive notifications). If the Edge token matches the target token, update it in the same Saturday rotation window. If Hetzner differs from phone BotA, plan separate revocation; dividend scanner is excluded only after confirming its token does not match a token actually being revoked. No raw token or credential-bearing URL. Saturday 28 Nov rotation not executed.

Historical runbooks and decision evidence restored in [docs/continuity-history](docs/continuity-history/README.md). Exact snapshots 83fa71e and 37dfacf preserve the October and November evidence; they are historical, not operational instructions.

Offline verification: preregistered D1 freshness 5/5; shared exposure/ID/expiry 12/12; all 12 focused offline suites passed (146 tests). No merge/deploy authorized. Remaining pre-activation gates: independent review, reconcile existing ACTIVE/backlog, then separate founder approval. Historical replay and clean-producer natural lifecycle gate remain open.
