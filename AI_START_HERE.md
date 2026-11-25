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

11 Nov EURUSD winner +20.8 pips legacy-created; 12 Nov GBPUSD cancellation legacy-performed; 23 Nov six overlapping Hetzner USDJPY BUY losses total -131.6 pips. Historical ledger mixed, not strategy-validation evidence. D1 writer/reader path mismatch falls back to ANY; future mutable-root fail-closed fix not deployed. Candidate one ACTIVE per pair+direction requires historical replay counting removed winners and losses. Yahoo provider unchanged; local quota warnings not evidence of Twelve Data billing. Preserve all strategy boundaries. Do not tune or repair code during retirement.

## Exactly one next action

Ask for explicit founder approval for obsolete credential backup cleanup only. Do not repeat phone/credential audits, restart services, invoke another broad Claude review, or change strategy. See canonical record for detailed evidence and remaining uncertainty.
