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
TELEGRAM_CONSUMER_INVENTORY=COMPLETE
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
NEXT_ACTION=PRESENT_FINAL_SATURDAY_ROTATION_PLAN_BEFORE_EXECUTION
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
| Telegram token rotation | Pending, Saturday approved subject to final execution plan and FX closure | Consumer inventory complete; shared BotA token only |
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

Telegram rotation was explicitly excluded from the approved Supabase change. It remains a necessary separate retirement gate because the phone reportedly retains a valid TELEGRAM_BOT_TOKEN. The consumer fingerprint comparison is complete: Hetzner and phone BotA match, dividend scanner differs, and the Supabase send-telegram dashboard digest differs (different-token conclusion INFERRED). Earlier checked 24-hour window had no send-telegram invocations; laptop dividend repository had no live .env. Do not assume separate variable names prove separate tokens.

Approved change window: Saturday 28 November 2026 during FX closure; confirm actual closure and send final plan before execution; consumer inventory complete. Rotate only the Telegram credential; preserve other credentials, verify old token rejection and new token authentication, and reconcile actual Telegram sends separately. No fabricated signal or restart.

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

- Telegram token rotation and reconciliation remain separate pending gates. Founder approved rotation on Saturday 28 Nov during FX closure; send plan before execution. Consumer inventory COMPLETE; no Edge or dividend-scanner secret change.
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

Present the final execution plan before starting the approved Saturday rotation during FX closure. Deployment is separately blocked until both timestamped hard preconditions (zero ACTIVE signals and zero pending ProfitLab retries) pass and the founder authorizes merge/deploy. Do not repeat completed audits, rotate keys before the approved window, merge, deploy, restart services, fabricate signals, or start strategy evaluation. Founder approval is not required for this isolated branch work. Keep natural lifecycle observation open under the approved extension rule.

## Branch review update - 25 November 2026

Founder accepted the D1 mutable-root fail-closed reader, visible DEGRADED health and release credential-file guard, subject to the pre-registered 36-hour freshness requirement. Missing, unparseable or stale updated_at is UNAVAILABLE/stale, including health reason d1_cache:<PAIR>:stale. Exposure admission is a durable local pair+direction record before accepted CSV/Telegram, with a UUID assigned at admission and propagated to both Supabase publication paths. Only the confirmed CLOSED/CANCELLED row with the matching signal ID and scope releases its record; changed SL/TP does not invalidate the ID match. Normal expiry 24h with usable candle coverage for orphan records; hard expiry 168h. A late retry for a replaced/expired admission cannot insert an old ACTIVE row; the sink checks its admission ID, not delivery status, and exact retries dedup by ID even after closure. Admission does not query Supabase ACTIVE rows or delivery state; each sink retains its independent retry behavior. This is isolated candidate code, NOT a production rollout. Merge/deploy remain unauthorized. Pre-activation requires zero ACTIVE rows and zero pending ProfitLab retries, verified at deploy time; no reconciliation code. Late-retry rejection is covered by offline tests. Hard expiry is a local safety release, not proof a remote row closed during an outage.

Telegram plan Step 1: SHA-256(raw token), first 12 hex only. Founder REPORTED phone BotA token fingerprint 7e18d1067664 and dividend-capture-scanner token fingerprint 4adf3e925f93 (different from phone BotA). Founder REPORTED OANDA practice endpoint in both phone files; OANDA token cleanup low priority. Hetzner BotA token fingerprint VERIFIED by SSH: 7e18d1067664, matching the reported phone BotA token. The reported dividend scanner token 4adf3e925f93 differs and is excluded. Supabase send-telegram SHA-256 dashboard digest prefix 8fac38826d87 is VERIFIED from the founder-provided dashboard screenshot; it does not match 7e18d1067664. INFERRED: the Edge token is different, assuming the dashboard digest is SHA-256 of the raw value, the same method used for 7e18d1067664. Deployed send-telegram v38 reads TELEGRAM_BOT_TOKEN and TELEGRAM_ADMIN_CHAT_ID; known callers are ProfitLab Account.tsx admin test action and deployed stripe-webhook v48 (new subscription, active update/renewal, cancellation/inactive notifications). Exclude the Edge token from Saturday rotation; do not modify the Edge secret. The mandatory final ProfitLab administrator test confirms send-telegram operation. No separate phone BotA token revocation is required; the shared old token is the Saturday rotation target. No raw token or credential-bearing URL. Saturday 28 Nov rotation not executed.

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

Telegram consumer inventory: COMPLETE (identified consumers, fingerprint comparison finished).

| Consumer | SHA-256 first 12 | Evidence | Saturday decision |
|---|---|---|---|
| Hetzner BotA | 7e18d1067664 | VERIFIED by SSH | Rotate |
| Phone BotA | 7e18d1067664 | REPORTED by founder | Invalidated by rotation |
| Dividend-capture-scanner | 4adf3e925f93 | REPORTED by founder | Excluded |
| Supabase send-telegram | 8fac38826d87 | Dashboard digest VERIFIED; different-token conclusion INFERRED | Excluded; do not modify Edge secret |

INFERRED: the Edge token is different, assuming the dashboard digest is SHA-256 of the raw value, the same method used for 7e18d1067664.

### Saturday 28 November Telegram sequence (approved FX-closure window, not executed)

1. Confirm FX closure and read-only Supabase ACTIVE count = 0; record both preflight results and UTC timestamps. Confirm the completed consumer inventory and present the final execution plan to the founder before starting. Check that no scheduled Telegram-consuming child is using the old credential at the swap boundary. Do not restart services or alter scheduling.
2. Revoke the shared old BotA token via BotFather and obtain the replacement securely. The new token is visible only to the founder, who personally enters it at the hidden read -s prompt over interactive SSH. Never paste it into any chat. Retain the old value only in the guarded root-only rollback backup and protected transient test memory; never print either token or a credential-bearing URL.
3. Use the complete atomic-swap script below; atomically replace only TELEGRAM_BOT_TOKEN in /etc/bota/live-delivery.env, preserving owner, mode and every unrelated credential. Success stdout contains only the new SHA-256 fingerprint (first 12 hex). Do not modify the Supabase Edge secret or dividend scanner.
4. Run the preregistered getMe tests from Hetzner: exactly one old-token request expecting HTTP 401 and exactly one replacement-token request expecting HTTP 200. Record UTC time, source, call count and HTTP status only. No test message at this step. Stop on unexpected results.
5. Observe normal scheduled jobs and verify expected consumer operation. Dispose of transient obsolete token material securely; retain the protected rollback backup until step 7. No restoration of the revoked token, restart or unrelated credential change.
6. Mandatory final verification: press the ProfitLab Account administrator Telegram test button exactly once and confirm the genuine test message arrived. Record UTC send/test and receipt evidence, success/failure and recipient channel identity without raw credentials. This checks that send-telegram still works and addresses the digest-method caveat. No fabricated trading signal or subscription event. Failed or unverified receipt blocks rotation acceptance; investigate without changing the Edge secret. Natural trading-signal Telegram reconciliation remains separately pending.
7. Only after step 6 PASS: securely delete the exact swap rollback backup using the guarded shred procedure below; verify active credential file checksum unchanged and record UTC evidence. This backup contains the live Supabase key and health secret. No cleanup before the mandatory admin test passes.

Next action: present the final execution plan before Saturday execution. Consumer inventory COMPLETE. No rotation, merge or deployment has been executed by this update.

### Founder-approved Saturday execution safeguards

Preflight: record UTC timestamp, read-only Supabase production ACTIVE count = 0, confirmed FX closure, and no conflicting Telegram-consuming child at the swap boundary. Nonzero or unprovable ACTIVE count means STOP; do not revoke the token, manufacture/close signals, or change scheduling to pass. The separate repair deployment preconditions and approval remain unchanged.

The new BotFather token is shown only to the founder. Never paste it into ChatGPT, Claude, another chat, shell history, command arguments or logs. The founder personally opens an interactive SSH terminal to Hetzner as root and runs the complete script below only on Saturday after preflight. Save the script without any token embedded, then execute with bash in the interactive terminal; enter the token only at the hidden read -s prompt. Success stdout is solely the new raw-value SHA-256 fingerprint (first 12 hexadecimal characters); the prompt and fixed errors are stderr. Never read out the backup or credential file. Do not use an assistant-controlled terminal for secret entry.

The exact root-only 0600 rollback path is /etc/bota/.live-delivery.rollback-telegram-20261128. It contains the original revoked Telegram token AND the live Supabase key and health secret. Retain it for the single old-token getMe rejection test, loading the old value directly in protected process memory from the backup and the new value directly from the active file. Print only test timestamps, source, counts and HTTP statuses; no URL, response body or tokens. Never restore the revoked token. A failure stops execution; verify actual state without exposing credentials before any recovery. Do not create a second backup.

#### Complete atomic-swap script (prepared, not executed on production)

~~~bash
#!/usr/bin/env bash
set +x
set -euo pipefail
umask 077
ulimit -c 0
test "$(id -u)" = 0
test -t 0
trap 'unset new_token' EXIT
IFS= read -r -s -p 'Enter replacement BotFather token (hidden): ' new_token </dev/tty
printf '\n' >&2
printf '%s' "$new_token" | python3 -c '
import os, sys, re, stat, hashlib, pwd, grp, tempfile
from pathlib import Path

active = Path("/etc/bota/live-delivery.env")
backup = Path("/etc/bota/.live-delivery.rollback-telegram-20261128")
expected_old = "7e18d1067664"
staged = None
def require(ok):
    if not ok:
        raise ValueError("rotation_precondition_failed")
def sync_parent():
    fd = os.open(active.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
def identity(s):
    return (s.st_dev, s.st_ino, s.st_uid, s.st_gid, s.st_mode,
            s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
def write_secure(fd, data, uid, gid):
    with os.fdopen(fd, "wb") as f:
        os.fchmod(f.fileno(), 0o600)
        os.fchown(f.fileno(), uid, gid)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
try:
    new = sys.stdin.buffer.read()
    require(re.fullmatch(rb"[0-9]+:[A-Za-z0-9_-]+", new) is not None)
    require(0 < len(new) <= 256)
    uid = pwd.getpwnam("bota").pw_uid
    gid = grp.getgrnam("bota").gr_gid
    require(not os.path.lexists(backup))
    with os.fdopen(os.open(active, os.O_RDONLY | os.O_NOFOLLOW), "rb") as f:
        before = os.fstat(f.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1)
        require((before.st_uid, before.st_gid, stat.S_IMODE(before.st_mode)) == (uid, gid, 0o600))
        original = f.read()
    pattern = rb"(?m)^([ \t]*TELEGRAM_BOT_TOKEN=)([^\r\n]*)(\r?)$"
    matches = list(re.finditer(pattern, original))
    require(len(matches) == 1)
    m = matches[0]
    old = m.group(2).strip()
    if len(old) >= 2 and old[:1] in (b"\x22", b"\x27") and old[-1:] == old[:1]:
        old = old[1:-1]
    require(hashlib.sha256(old).hexdigest()[:12] == expected_old)
    require(new != old)
    # Replace only the matched value; all other bytes are untouched.
    replacement = original[:m.start(2)] + new + original[m.end(2):]
    require(identity(active.lstat()) == identity(before))
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    write_secure(fd, original, 0, 0)
    sync_parent()
    fd, staged = tempfile.mkstemp(prefix=".live-delivery.telegram.", dir=active.parent)
    write_secure(fd, replacement, uid, gid)
    require(identity(active.lstat()) == identity(before))
    os.replace(staged, active)
    staged = None
    sync_parent()
    require(active.read_bytes() == replacement)
    installed = active.lstat()
    require(stat.S_ISREG(installed.st_mode) and installed.st_nlink == 1)
    require((installed.st_uid, installed.st_gid, stat.S_IMODE(installed.st_mode)) == (uid, gid, 0o600))
    print(hashlib.sha256(new).hexdigest()[:12])
except Exception:
    print("ERROR: rotation stopped; inspect state without displaying credentials; do not retry blindly.", file=sys.stderr)
    sys.exit(1)
finally:
    if staged is not None:
        try:
            os.unlink(staged)
        except OSError:
            pass
'
unset new_token
~~~

#### Step 7: guarded backup deletion (only after step 6 PASS)

After old/new getMe checks, normal scheduled operation and the single ProfitLab admin test receipt have all passed, delete only this exact backup as root with the previously accepted guarded shred procedure. This cleanup is approved conditional on step 6 PASS. If a prerequisite fails, STOP; do not delete the backup or claim rotation complete. Verify the PASS line and record UTC time. Secure overwrite on virtual disks, SSDs, snapshots and copy-on-write storage is not guaranteed; deleting the backup does not rotate the unrelated live credentials.

~~~bash
#!/usr/bin/env bash
set +x
set -euo pipefail
backup=/etc/bota/.live-delivery.rollback-telegram-20261128
active=/etc/bota/live-delivery.env
test "$(id -u)" = 0
test -f "$backup"
test ! -L "$backup"
test "$(stat -c '%u:%g:%a:%h' "$backup")" = "0:0:600:1"
test ! "$backup" -ef "$active"
test -f "$active"
test ! -L "$active"
before=$(sha256sum -- "$active")
shred -n 3 -z -u -- "$backup"
test ! -e "$backup"
test ! -L "$backup"
test "$(sha256sum -- "$active")" = "$before"
echo "PASS: Telegram rollback backup removed; active credentials unchanged"
~~~

Validation: bash syntax and synthetic local fixture tests for value-only swap, old-fingerprint rejection, existing-backup refusal, file permissions, fingerprint-only stdout and guarded deletion passed. Production script has not been executed. The actual hidden entry and server ownership/path checks remain Saturday execution gates.
