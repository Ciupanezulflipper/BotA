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
TELEGRAM_ROTATION_AUTHORIZED=NO
TELEGRAM_RECONCILIATION=PENDING
CREDENTIAL_BACKUP_CLEANUP=READY_AWAITING_FOUNDER_APPROVAL
LEGACY_RETIREMENT_COMPLETE=NO
CLEAN_72H_WINDOW=OPEN_T0_PROPOSED
PHONE_REMAINING_API_KEYS=PENDING_REVIEW
REPAIR_BRANCH=LOCAL_TESTS_ONLY_RED_BASELINE

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
PRODUCTION_CHANGE_AUTHORIZED=NO
CURRENT_PHASE=FINAL_RETIREMENT_GATES
NEXT_ACTION=FOUNDER_APPROVAL_FOR_CREDENTIAL_BACKUP_CLEANUP
FOUNDER_APPROVAL_REQUIRED=YES
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
| Telegram token rotation | Pending, not authorized | Phone reportedly retains valid token; consumer identity must be reconciled before separate rotation |
| Telegram reconciliation | Pending | Compare real Telegram output with Hetzner send records, independently of rotation |
| Credential backup cleanup | Ready – awaiting founder approval | Rollback file contains revoked key plus still-live Telegram and health secrets; no rollback value after revocation |

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
- `/etc/bota/.live-delivery.rollback-9tio_xxl` (reported root:root, mode 600) contains duplicate live Telegram token and health secret. Never restore it now that the old Supabase key is revoked. Remove only this exact file after explicit founder approval; verify active file unaffected. Do not delete or modify it during documentation work.

## Legacy producer and credential boundaries

The Android/Termux phone was an active production producer, not merely a control device. Phone-side closer timestamps matched Romanian-origin requests; phone and Hetzner shared the same old key fingerprint. The watchdog launcher `~/BotA/tools/start_native_service_daemon_watchdog.sh` was disabled. Earlier fresh-session proof included NO_BOTA_PROCESSES_PASS, closer and supervisor down, and no Romanian old-key traffic through 16:00 UTC. Reboot proof now supersedes the previous pending test. Do not repeat either test absent new evidence.

Modern BotA secret rotation did not rotate the project JWT or legacy service-role key. Earlier repository inspection found privileged ProfitLab/admin functions use separate SUPABASE_SERVICE_ROLE_KEY, not Hetzner SUPABASE_SERVICE_KEY. Functions included stripe-webhook, create-checkout, check-subscription, customer-portal, get-signals, sync-status, update-preferences, bota-health-admin and send-telegram. Separate health writes remained successful. Full Stripe/subscriber transaction testing was not performed; do not claim independently verified billing health.

GitHub Actions: historical-candle-acquisition.yml references SUPABASE_SERVICE_KEY only as empty for offline validation; no live secret injection found. Vercel: only LifVio projects observed, environment metadata 403, CLI unavailable; accidental key storage UNKNOWN. Laptop: C:\Users\tomag\Supabase key.txt contains a modern key of unverified identity; earlier runtime audit found no active BotA. Separate hygiene follow-up, not justification for repeated runtime audit.

## Separate Telegram gates

Telegram rotation was explicitly excluded from the approved Supabase change. It remains a necessary separate retirement gate because the phone reportedly retains a valid TELEGRAM_BOT_TOKEN. Exact token identity between Hetzner, phone, Supabase admin-only send-telegram (TELEGRAM_ADMIN_CHAT_ID), and dividend scanner (TELEGRAM_TOKEN) is not fully established. Earlier checked 24-hour window had no send-telegram invocations; laptop dividend repository had no live .env. Do not assume separate variable names prove separate tokens.

Proposed change window: weekend FX closure, approximately Friday 22:00 UTC to Sunday 22:00 UTC (27–29 November 2026; confirm actual schedule). Before approval, bound consumer inventory, replacement and verification steps. Rotate only with explicit approval, revoke the legacy token, confirm expected consumers work, and separately reconcile actual Telegram sends against Hetzner records. No manufactured signals or notifications solely to satisfy lifecycle evidence. Phone is Supabase-disabled and stopped, but overall retirement is not complete.

## Signal provenance and strategy boundary

- 11 Nov EURUSD SELL +20.8 pips: created by Romanian legacy phone, not Hetzner; Hetzner HOLD/filter rejection; both closers later touched row.
- 12 Nov GBPUSD SELL: created by Hetzner, cancelled by legacy phone.
- 23 Nov USDJPY: six overlapping GREEN M15 BUYs from Hetzner between 14:15 and 16:30 UTC, losses -20.5, -22.5, -22.4, -21.6, -21.7, -22.9; total -131.6 pips.
- Mixed producer/generation ledger is operational evidence, not clean strategy validation. Do not use obsolete LOSS -> WIN -> CANCELLED sequence.
- Candidate one ACTIVE per pair+direction control approved for tests-only branch work; implementation/deployment not authorized. Replay historical episodes counting removed winners and losses.
- D1 writer uses BOTA_MUTABLE_ROOT (/var/lib/bota/cache); scoring reader uses ROOT/BOTA_ROOT and silently falls back to ANY. Recent GREEN signals lacked effective D1 confirmation. Future repair: mutable-root read and fail closed/alert; not deployed.
- Yahoo is frozen production candle provider. Generic 600/800 or 960/800 warnings are not evidence of Twelve Data billing; prior audit found no Twelve Data production calls. No quota purchase warranted on those warnings.
- POLICY_B_ACCEPTED=195; PRE_REGISTERED_KILL_THRESHOLD=400; HISTORICAL_CORPUS_GATE=FAIL; STRATEGY_EDGE_VALIDATED=NO. No tuning Policy B, indicators, ADX/RSI, pairs, timeframe, H1/D1 confirmation, TP/SL, news or provider policy during retirement.

## 25 Nov — observation boundary, residual hazards and tests-only branch

### 72-hour clean-producer acceptance

VERIFIED: founder reported deletion of bota_service; exact dashboard deletion time UNKNOWN. One deliberate GET /rest/v1/signals from bota-r5-01 (2.29.4.127) using revoked key returned HTTP 401 at terminal UTC 2026-11-24T19:59:56.371343Z; independent Edge record 19:59:56.410Z. The next new-key GET returned HTTP 200 at 20:00:01.036Z. No repeat rejection call necessary. Formal pre-registered T0 not evidenced. INFERRED conservative proposed T0: 2026-11-24T20:00:01.036Z; earliest 72-hour end 2026-11-27T20:00:01.036Z (22:00:01 Romania). Keep window open until one real Hetzner signal is created and closed with verified provenance; never fabricate a signal. Unexpected producer activity blocks acceptance and requires investigation and a new clean boundary. Latest accepted overnight evidence ends 2026-11-25T10:18:00Z: 55/55 DB reads, 164/164 health reports, zero legacy requests and unexpected producers. Window is NOT passed.

REPORTED phone reboot persistence PASS. Airplane mode during reboot UNKNOWN; absence of phone Telegram calls UNKNOWN. Supabase logs cannot prove absence of Telegram traffic. Do not repeat completed reboot or key tests to fill the historical gap.

### Residual credential gates

- Telegram token rotation and reconciliation remain separate pending gates; phone reportedly retains valid TELEGRAM_BOT_TOKEN. Proposed window 27 Nov 22:00 UTC to 29 Nov 22:00 UTC, subject to actual FX schedule and explicit founder approval. Inventory consumers first.
- Obsolete rollback backup /etc/bota/.live-delivery.rollback-9tio_xxl: ready, awaiting explicit founder approval. Revoked key has no rollback value; duplicate live Telegram and health secrets remain. Proposed root deletion: verify exact path is regular, not symlink or hardlink, root:root mode 600, different inode from active file; shred -n 3 -z -u -- /etc/bota/.live-delivery.rollback-9tio_xxl; confirm absence and unchanged active-file checksum without printing secrets. Overwrite not guaranteed on virtual/COW/SSD/snapshot storage. Not executed.
- Phone remaining API keys: pending review. OANDA_API_URL in ~/BotA/.env.runtime UNKNOWN; read only the URL on device, never token. api-fxpractice.oanda.com = practice; api-fxtrade.oanda.com = live, potential money-risk; escalate live credential review/rotation for separate approval. No trading API calls.

### Lessons and deployment hazard

REPORTED historical cause of 6 Sep failed retirement: two startup paths (boot script and $PREFIX/etc/profile.d/start-services.sh); only one was disabled. Future retirement checklist must cover both boot and shell/profile startup, then persistence proof. Do not restart or repeat completed tests now.

VERIFIED deployed run_signal_closer_live.sh exports values from config/strategy.env, .env and .env.runtime, potentially overwriting inherited credentials. be_shadow_manager.py loads .env.runtime, .env, config/strategy.env and strategy.env using os.environ.setdefault, so it fills missing values rather than overwriting an existing environment variable. Other legacy readers remain a risk. REPORTED from prior Claude server check: none of those files existed in the deployed release. Proposed deployment guard (not implemented): before staging/activation, fail the candidate release if any of .env, .env.runtime, config/strategy.env, strategy.env exists or is a symlink (including broken symlinks); keep credentials external, report offending paths only, never contents. Test in isolation before approval.

### Approved tests-only repair work

Branch fix/retirement-d1-active-signal-tests-20261125, laptop WSL isolated worktree /home/tomag/BotA-retirement-tests-20261125, local commit 762f942ecb6af45a13e83230bfd36ab93601219a. Base 166f32bec5a8d03273129ddf0246ace0f2a2e486; verified only documentation differs from deployed release 83fa71e651483c95096ce635b525cacbf91cbc5d. Recreated durable local tests-only worktree because prior scratch commit 013ae4f78a7ffb853fb2c5c66301787abd6b33cc was not pushed and unavailable in current session; no duplicate production audit. Only tests/test_retirement_repair_acceptance.py changed, clean worktree after commit. Not pushed, no CI, no deployment.

Offline baseline test_r5_mutable_root_scoring.py (3/3) and test_supabase_exact_dedup.py (8/8) PASS. New acceptance suite (2 PASS, 4 expected assertion failures): conflicting release-cache preference; missing mutable cache permits BUY; invalid mutable trend permits BUY; second distinct same-pair/direction ACTIVE causes POST. Opposite direction and closed predecessor controls PASS. D1 tests execute actual inline decision block; publisher tests exercise actual publisher with in-memory REST fake, no network. Health-alert integration and both-sink/atomic admission coverage remain pending; no implementation code changed. Existing exact-dedup tests explicitly allowed distinct same-direction entries, so supersede that contract deliberately when implementing the approved new exposure policy; preserve exact-retry dedup and independent delivery evidence. Historical replay must count removed winners/losses. No claim of repaired behavior yet.

Both repairs deployed = NEW strategy generation. Evaluation starts at the later of (both repairs deployed) and (72-hour clean-producer acceptance passed, including any extension). No deployment, strategy evaluation or live-money trading authorized.

Existing draft documentation PRs BotA #139 and obsidian-engineering-knowledge #90 are unmerged and may contain stale guidance; do not merge blindly over these canonical records. No PR merge performed.

## Exactly one next action

Obtain explicit founder approval to remove the obsolete rollback file only, since it duplicates live credentials and no longer provides rollback. Documentation approval is not cleanup approval.

After that gate, prepare separate Telegram rotation for the proposed weekend closure; continue natural lifecycle observation and Telegram reconciliation. Do not restart services, repeat completed phone or credential tests, request a broad AI audit, manufacture signals, or make strategy/code changes. No further production mutation currently authorized.
