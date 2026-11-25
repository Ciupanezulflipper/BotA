# BotA AI Start Here

Last updated: **2026-11-25 UTC**

Read before proposing strategy, deployment, Telegram, ProfitLab, Android/Termux, VPS, replay or runtime work.

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
TELEGRAM_ROTATION_AUTHORIZED=NO
TELEGRAM_RECONCILIATION=PENDING
CREDENTIAL_BACKUP_CLEANUP=READY_AWAITING_FOUNDER_APPROVAL
LEGACY_RETIREMENT_COMPLETE=NO
CLEAN_72H_WINDOW=OPEN_T0_PROPOSED
PHONE_REMAINING_API_KEYS=PENDING_REVIEW
REPAIR_BRANCH=LOCAL_TESTS_ONLY_RED_BASELINE
RECENT_LEDGER_PROVENANCE=CROSS_CONTAMINATED
D1_REPAIR_DEPLOYED=NO
ONE_ACTIVE_PAIR_DIRECTION_CONTROL_DEPLOYED=NO
POLICY_B_ACCEPTED=195
PRE_REGISTERED_KILL_THRESHOLD=400
HISTORICAL_CORPUS_GATE=FAIL
STRATEGY_EDGE_VALIDATED=NO
STRATEGY_TUNING=NO
PRODUCTION_CHANGE_AUTHORIZED=NO
NEXT_ACTION=FOUNDER_APPROVAL_FOR_CREDENTIAL_BACKUP_CLEANUP
FOUNDER_APPROVAL_REQUIRED=YES
```

## Accepted evidence — do not repeat

- Legacy phone was a real producer sharing Hetzner's old Supabase key. Watchdog and runit stopped, launcher disabled, fresh-session and reboot persistence checks passed.
- Dedicated modern secret installed atomically at 19:27:30 UTC on 24 Nov without restart; other credentials preserved. Exact dashboard match established old key identity.
- New key authenticated at 19:28:44 UTC; scheduled closer reads 19:30 and 19:45 HTTP 200. Claude Code reported all relevant jobs succeeded and no credential override files existed. Successful job exits are not proof of writes.
- Old key revoked; deliberate rejection 19:59:56 HTTP 401 independently logged, new key read 20:00:01 HTTP 200.
- Overnight 24 Nov 20:39–25 Nov 10:18 UTC: 55/55 Hetzner reads, 164/164 health writes, zero legacy key requests and unexpected producers. No actual signal creation/closure in that window.
- ProfitLab privileged Edge Functions use separate legacy service-role path; health requests use a separate credential. Full billing transaction testing not performed.

## Remaining gates

1. Credential backup cleanup: ready, explicit founder approval required. Exact obsolete rollback file `/etc/bota/.live-delivery.rollback-9tio_xxl` contains duplicate live Telegram and health secrets. Old Supabase key cannot be restored.
2. Telegram token rotation: separate pending gate, not authorized. Phone reportedly still holds valid token. Inventory Hetzner, Supabase send-telegram, phone and dividend scanner; propose Fri ~22:00–Sun ~22:00 UTC FX closure (27–29 Nov; confirm schedule).
3. Natural signal lifecycle: pending real Hetzner creation and closure; never manufacture signals.
4. Telegram reconciliation: separate pending gate against Hetzner send records.
5. Overall retirement not complete. No new production mutation approved.

## Strategy and provenance

11 Nov EURUSD winner +20.8 pips legacy-created; 12 Nov GBPUSD cancellation legacy-performed; 23 Nov six overlapping Hetzner USDJPY BUY losses total -131.6 pips. Historical ledger mixed, not strategy-validation evidence. D1 writer/reader path mismatch falls back to ANY; future mutable-root fail-closed fix not deployed. Candidate one ACTIVE per pair+direction approved for tests-only branch work; implementation/deployment not authorized; requires historical replay counting removed winners and losses. Yahoo provider unchanged; local quota warnings not evidence of Twelve Data billing. Preserve all strategy boundaries. Do not tune or repair code during retirement.

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

Ask for explicit founder approval for obsolete credential backup cleanup only. Do not repeat phone/credential audits, restart services, invoke another broad Claude review, or change strategy. See canonical record for detailed evidence and remaining uncertainty.
