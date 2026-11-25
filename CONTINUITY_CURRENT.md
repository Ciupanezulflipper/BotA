# BotA Current Continuity State

Last updated: **2026-11-25 UTC**

Canonical operational handoff. Historical audits are evidence, not current instructions.

## Current authoritative status

```text
BOTA_EDGE_STATUS=UNVALIDATED
LIVE_MONEY_TRADING=NO
PRIMARY_RUNTIME=HETZNER
HETZNER_RUNTIME_STATE=ACTIVE
DEPLOYED_RELEASE=83fa71e651483c95096ce635b525cacbf91cbc5d
PROVIDER=YAHOO
PAIR_SCOPE=EURUSD,GBPUSD,USDJPY
TIMEFRAME=M15

LEGACY_ANDROID_PRODUCER_PROVEN=YES
LEGACY_ANDROID_RUNTIME=STOPPED
LEGACY_ANDROID_KNOWN_RESTART_PATH=DISABLED
FRESH_TERMUX_SESSION_RESTART_TEST=PASS
PHONE_REBOOT_TEST=PASS
SUPABASE_KEY_TYPE=MODERN_SB_SECRET
SUPABASE_ROTATION=COMPLETE
HETZNER_DEDICATED_KEY=bota_hetzner
OLD_SHARED_KEY=bota_service
OLD_SHARED_KEY_REVOKED=YES
OLD_KEY_REJECTION_TEST=PASS
OVERNIGHT_PRODUCTION_STABILITY=PASS
CLEAN_SIGNAL_LIFECYCLE=PENDING
TELEGRAM_CONSUMER_INVENTORY=INCOMPLETE
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
11_NOV_WIN_HETZNER=NO
12_NOV_CANCEL_HETZNER=NO
23_NOV_USDJPY_HETZNER_CLUSTER=6_LOSSES_-131.6_PIPS
D1_CONFIRMATION_READER_PATH_DEFECT=VERIFIED
D1_REPAIR_DEPLOYED=NO
ONE_ACTIVE_PAIR_DIRECTION_CONTROL_DEPLOYED=NO
POLICY_B_ACCEPTED=195
PRE_REGISTERED_KILL_THRESHOLD=400
HISTORICAL_CORPUS_GATE=FAIL
STRATEGY_EDGE_VALIDATED=NO
STRATEGY_TUNING=NO
PAIR_CHANGES=NO
TIMEFRAME_CHANGES=NO
PRODUCTION_CHANGE_AUTHORIZED=NO_EXCEPT_APPROVED_2026-11-28_TELEGRAM_ROTATION_AFTER_PLAN
CURRENT_PHASE=FINAL_RETIREMENT_GATES
NEXT_ACTION=COMPLETE_TELEGRAM_FINGERPRINT_COMPARISON
FOUNDER_APPROVAL_REQUIRED=YES_FOR_MERGE_OR_DEPLOY
```

## Completed milestones and evidence

| Gate | State | Evidence |
|---|---|---|
| Legacy phone shutdown and launcher disable | PASS | Watchdog stopped first, runit services down, known launcher non-executable, fresh Termux session did not resurrect processes |
| Dedicated Hetzner Supabase key | PASS | Dashboard key bota_hetzner created; exact hidden comparison identified bota_service as old key |
| Atomic replacement | PASS | 2026-11-24 19:27:30 UTC; owner bota:bota, mode 600; unrelated credentials preserved |
| Authentication | PASS | 19:28:44 UTC manual read HTTP 200; independent Edge log matched Hetzner |
| Scheduled job verification | PASS (read and job execution only) | Claude Code reported watcher, profitlab_delivery, closer passed; closer GET at 19:30 and 19:45 returned 200; no restart |
| Old key revocation | PASS | Dashboard deletion reported by founder; 19:59:56 UTC deliberate old-key read HTTP 401, independently logged; new key GET HTTP 200 at 20:00:01 |
| Phone reboot persistence | PASS | Founder rebooted phone; post-reboot `ps -A -o pid,args` filtered for BotA/watchdog/runsv returned no output |
| Overnight observation | PASS | 2026-11-24 20:39 to 2026-11-25 10:18 UTC: 55/55 Hetzner DB reads and 164/164 health writes HTTP 200; zero legacy key requests and unexpected producers observed |
| Real Hetzner signal created and closed | Pending | No natural new signal write in observed window; do not fabricate signals |
| Telegram token rotation | Pending, Saturday approved subject to plan and digest | Phone reportedly retains valid token; consumer identity must be reconciled before separate rotation |
| Telegram reconciliation | Pending | Compare real Telegram output with Hetzner send records, independently of rotation |
| Credential backup cleanup | PASS | Founder approved exact deletion; root SSH script returned PASS: Backup removed; active credentials unchanged |

Evidence labels: VERIFIED = terminal output, directly observed dashboard or Supabase logs, exact deployed GitHub code; REPORTED = Claude Code server findings and founder actions not independently rechecked; INFERRED = conclusion requiring evidence; UNKNOWN = insufficient evidence. No claims beyond the observation window. Passing Supabase reads and successful job exits do not prove real signal writes.

## Supabase rotation record

Production project: ozgkeslgjqbqfewojnmr. Hetzner source: 2.29.4.127.

- Old local SHA256 prefix: fe77f4b4b813; new: 3d16a7ef7e6e. These local prefixes differ from Supabase Edge key hashes.
- Old Edge fingerprint: _nf0tLgT5ufjgvyN5_q7t5f7Z-BFzOAvaY6f3I9etuM.
- New Edge fingerprint: PRan735ux43M84jBfPfjfyKmmOFSZTiYOne3nF5yCPg.
- Health Edge fingerprint: bIT1NJwn3x28hOS6PJW-ebioiqs86mYrEaIJXVLAk-s; downstream health writer 3.69.175.7, separate credential. Claude Code attributed this to the health-ingest Edge Function.
- Prior to revocation, no old fingerprint use was observed after swap. The sole deliberately rejected old-key request at 19:59:56 was the authorized rejection test, not rogue phone traffic.
- During 19:59:50–20:39 UTC on 24 Nov, three successful Hetzner reads and eight successful health writes; no unexpected legacy attempts.
- During the overnight window, only 55 successful Hetzner GET /rest/v1/signals and 164 successful POST /rest/v1/bot_runtime_health were returned. No trading signal writes occurred.
- Deployed `tools/vps_orchestrator.py` reloads `/etc/bota/live-delivery.env` for each approved child (watcher, closer, profitlab_delivery), strips inherited aliases, and fails closed on invalid file. No service restart required.
- `tools/run_signal_closer_live.sh` can override inherited keys from config/strategy.env, .env and .env.runtime. Claude Code reported those files absent on the deployed server, no competing source, and zero service restarts. Future config additions must not override the credential.
- Obsolete rollback file `/etc/bota/.live-delivery.rollback-9tio_xxl` deleted under explicit founder approval. Root SSH verification: PASS: Backup removed; active credentials unchanged.

## Legacy producer and credential boundaries

The Android/Termux phone was an active production producer, not merely a control device. Phone-side closer timestamps matched Romanian-origin requests; phone and Hetzner shared the same old key fingerprint. The watchdog launcher `~/BotA/tools/start_native_service_daemon_watchdog.sh` was disabled. Earlier fresh-session proof included NO_BOTA_PROCESSES_PASS, closer and supervisor down, and no Romanian old-key traffic through 16:00 UTC. Reboot proof now supersedes the previous pending test. Do not repeat either test absent new evidence.

Modern BotA secret rotation did not rotate the project JWT or legacy service-role key. Earlier repository inspection found privileged ProfitLab/admin functions use separate SUPABASE_SERVICE_ROLE_KEY, not Hetzner SUPABASE_SERVICE_KEY. Functions included stripe-webhook, create-checkout, check-subscription, customer-portal, get-signals, sync-status, update-preferences, bota-health-admin and send-telegram. Separate health writes remained successful. Full Stripe/subscriber transaction testing was not performed; do not claim independently verified billing health.

GitHub Actions: historical-candle-acquisition.yml references SUPABASE_SERVICE_KEY only as empty for offline validation; no live secret injection found. Vercel: only LifVio projects observed, environment metadata 403, CLI unavailable; accidental key storage UNKNOWN. Laptop: C:\Users\tomag\Supabase key.txt contains a modern key of unverified identity; earlier runtime audit found no active BotA. Separate hygiene follow-up, not justification for repeated runtime audit.

## Separate Telegram gates

Telegram rotation was explicitly excluded from the approved Supabase change. It remains a necessary separate retirement gate because the phone reportedly retains a valid TELEGRAM_BOT_TOKEN. Exact token identity between Hetzner, phone, Supabase admin-only send-telegram (TELEGRAM_ADMIN_CHAT_ID), and dividend scanner (TELEGRAM_TOKEN) is not fully established. Earlier checked 24-hour window had no send-telegram invocations; laptop dividend repository had no live .env. Do not assume separate variable names prove separate tokens.

Approved change window: Saturday 28 November 2026 during FX closure; confirm actual closure, inventory consumers and send plan before execution. Rotate only the Telegram credential; preserve other credentials, verify old token rejection and new token authentication, and reconcile actual Telegram sends separately. No fabricated signal or restart.

## Signal provenance and strategy boundary

- 11 Nov EURUSD SELL +20.8 pips: created by Romanian legacy phone, not Hetzner; Hetzner HOLD/filter rejection; both closers later touched row.
- 12 Nov GBPUSD SELL: created by Hetzner, cancelled by legacy phone.
- 23 Nov USDJPY: six overlapping GREEN M15 BUYs from Hetzner between 14:15 and 16:30 UTC, losses -20.5, -22.5, -22.4, -21.6, -21.7, -22.9; total -131.6 pips.
- Mixed producer/generation ledger is operational evidence, not clean strategy validation. Do not use obsolete LOSS -> WIN -> CANCELLED sequence.
- Candidate one ACTIVE per pair+direction control approved for isolated branch implementation; merge/deployment not authorized. Replay historical episodes counting removed winners and losses.
- D1 writer uses BOTA_MUTABLE_ROOT (/var/lib/bota/cache); scoring reader uses ROOT/BOTA_ROOT and silently falls back to ANY. Recent GREEN signals lacked effective D1 confirmation. Future repair: mutable-root read and fail closed/alert; not deployed.
- Yahoo is frozen production candle provider. Generic 600/800 or 960/800 warnings are not evidence of Twelve Data billing; prior audit found no Twelve Data production calls. No quota purchase warranted on those warnings.
- POLICY_B_ACCEPTED=195; PRE_REGISTERED_KILL_THRESHOLD=400; HISTORICAL_CORPUS_GATE=FAIL; STRATEGY_EDGE_VALIDATED=NO. No tuning Policy B, indicators, ADX/RSI, pairs, timeframe, H1/D1 confirmation, TP/SL, news or provider policy during retirement.

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

Complete the remaining Supabase Edge token digest comparison before Saturday rotation. Deployment is separately blocked until both timestamped hard preconditions (zero ACTIVE signals and zero pending ProfitLab retries) pass and the founder authorizes merge/deploy. Do not repeat completed audits, rotate keys before the approved window, merge, deploy, restart services, fabricate signals, or start strategy evaluation. Founder approval is not required for this isolated branch work. Keep natural lifecycle observation open under the approved extension rule.

## Branch review update - 25 November 2026

Founder accepted the D1 mutable-root fail-closed reader, visible DEGRADED health and release credential-file guard, subject to the pre-registered 36-hour freshness requirement. Missing, unparseable or stale updated_at is UNAVAILABLE/stale, including health reason d1_cache:<PAIR>:stale. Exposure admission is a durable local pair+direction record before accepted CSV/Telegram, with a UUID assigned at admission and propagated to both Supabase publication paths. Only the confirmed CLOSED/CANCELLED row with the matching signal ID and scope releases its record; changed SL/TP does not invalidate the ID match. Normal expiry 24h with usable candle coverage for orphan records; hard expiry 168h. A late retry for a replaced/expired admission cannot insert an old ACTIVE row; the sink checks its admission ID, not delivery status, and exact retries dedup by ID even after closure. Admission does not query Supabase ACTIVE rows or delivery state; each sink retains its independent retry behavior. This is isolated candidate code, NOT a production rollout. Merge/deploy remain unauthorized. Pre-activation requires zero ACTIVE rows and zero pending ProfitLab retries, verified at deploy time; no reconciliation code. Late-retry rejection is covered by offline tests. Hard expiry is a local safety release, not proof a remote row closed during an outage.

Telegram plan Step 1: SHA-256(raw token), first 12 hex only. Founder REPORTED phone BotA token fingerprint 7e18d1067664 and dividend-capture-scanner token fingerprint 4adf3e925f93 (different from phone BotA). Founder REPORTED OANDA practice endpoint in both phone files; OANDA token cleanup low priority. Hetzner BotA token fingerprint VERIFIED by SSH: 7e18d1067664, matching the reported phone BotA token. The reported dividend scanner token 4adf3e925f93 differs and is excluded. Supabase send-telegram token fingerprint UNKNOWN: connector has no secret-digest list; compare the existing project secret digest without retrieving raw value. Deployed send-telegram v38 reads TELEGRAM_BOT_TOKEN and TELEGRAM_ADMIN_CHAT_ID; known callers are ProfitLab Account.tsx admin test action and deployed stripe-webhook v48 (new subscription, active update/renewal, cancellation/inactive notifications). If the Edge token matches the target token, update it in the same Saturday rotation window. No separate phone BotA token revocation is required; the shared old token is the Saturday rotation target. No raw token or credential-bearing URL. Saturday 28 Nov rotation not executed.

Historical runbooks and decision evidence restored in [docs/continuity-history](docs/continuity-history/README.md). Exact snapshots 83fa71e and 37dfacf preserve the October and November evidence; they are historical, not operational instructions.

Offline verification: preregistered D1 freshness 5/5; shared exposure/ID/expiry 12/12; all 12 focused offline suites passed (146 tests). No merge/deploy authorized. Independent reviewer result REPORTED by founder: 62/62 retirement tests at f11a3ae; separate sandbox missing bota group was reported as environmental. Remaining pre-activation gates: zero ACTIVE rows and zero pending ProfitLab retries, both timestamped at deploy time, and separate founder approval. Historical replay and clean-producer natural lifecycle gate remain open.

## Founder-approved deployment and Saturday rotation plan - 25 November 2026

Independent reviewer result (REPORTED by founder): candidate f11a3ae, 62/62 retirement tests passed. A separate reviewer-sandbox failure was attributed to the missing local bota group, not to code. Do not repeat the accepted review merely to obtain another count.

### Hard deployment preconditions (operational checks only)

Merge and deployment remain NOT AUTHORIZED. No reconciliation code is requested or permitted by this decision. At the separately authorized deployment, before activation, record both read-only checks with actual UTC timestamps and evidence:

| Check | Required result | UTC evidence timestamp |
|---|---|---|
| Supabase production signals with status ACTIVE | 0 ACTIVE rows | Pending - capture at deployment time |
| ProfitLab delivery queue | 0 pending retries or in-flight delivery | Pending - capture at deployment time |

Use the production project and the current ProfitLab worker cursor, source end and retry/in-flight evidence; an unknown, missing, stale, malformed or reset cursor is not proof that the queue is drained. Check at the deployment boundary with no intervening producer or delivery work that could invalidate either result; if necessary, recheck within the authorized deployment procedure. If either check is nonzero or unprovable, STOP and defer deployment until both naturally pass. Do not fabricate, close, cancel, delete, skip, reconcile or reset signals or queues merely to pass these gates. Keep the existing release guard, independent review evidence and separate founder merge/deploy approval. No production checks are executed by this documentation update.

The new strategy evaluation starts only at the later of both repairs deployed and the approved 72-hour clean-producer window passed, including the natural-signal extension.

### Saturday 28 November Telegram sequence (approved window, not executed)

1. Confirm FX closure and token consumers. VERIFIED Hetzner BotA SHA256(raw token) prefix 7e18d1067664 matches founder-reported phone BotA prefix 7e18d1067664; dividend-capture-scanner prefix 4adf3e925f93 is different and excluded. OANDA practice endpoint reported; token cleanup low priority. Supabase send-telegram TELEGRAM_BOT_TOKEN digest remains UNKNOWN (founder message contains a placeholder, not a digest). Resolve before any revocation. Known callers: ProfitLab Account admin Telegram test and Stripe webhook subscription notifications (new, active update/renewal, cancellation/inactive).
2. Revoke the shared old bot token via BotFather and obtain its replacement using a secure input method; never print tokens or credential-bearing URLs.
3. Atomically replace /etc/bota/live-delivery.env, changing only TELEGRAM_BOT_TOKEN and preserving owner, mode and all unrelated credentials.
4. Immediately after the Hetzner swap: if the Edge digest equals 7e18d1067664, update the Supabase Edge secret TELEGRAM_BOT_TOKEN with the new token within the same Saturday window. If different, leave the Edge secret unchanged. If unknown, STOP before revocation (step 1).
5. Run the preregistered getMe tests from Hetzner: one old-token request expecting HTTP 401 and one replacement-token request expecting HTTP 200. Record UTC timestamp, source, call count and response status only. No test messages at this step. No restart or unrelated credential change.
6. Observe normal scheduled jobs and verify expected consumer operation. Secure obsolete credential copies according to the existing approval boundary; no restoration of a revoked token.
7. Final Saturday verification in BOTH digest outcomes: press the ProfitLab Account administrator Telegram test button exactly once and confirm the genuine test message arrived. Record UTC send/test and receipt evidence, success/failure and recipient channel identity without raw credentials. No fabricated trading signal or subscription event. A failed or unverified test blocks completion of rotation verification; genuine trading-signal Telegram reconciliation remains a separate pending gate.

Current blocker: obtain the first 12 hexadecimal characters of the Supabase Edge TELEGRAM_BOT_TOKEN SHA256 digest. No rotation, merge or deployment has been executed by this update.
