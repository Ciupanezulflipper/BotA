# BotA AI Start Here

Last updated: **2026-11-24 UTC**

Read this before proposing BotA strategy, deployment, Telegram, ProfitLab, Android/Termux, VPS/Hetzner, replay, historical-data or runtime work.

## Current authoritative truth

```text
PROJECT=BotA
BOTA_EDGE_STATUS=UNVALIDATED
LIVE_MONEY_TRADING=NO

PRIMARY_RUNTIME=HETZNER
HETZNER_RUNTIME_STATE=ACTIVE
DEPLOYED_RELEASE=83fa71e651483c95096ce635b525cacbf91cbc5d
PROVIDER=YAHOO
PAIRS=EURUSD,GBPUSD,USDJPY
TIMEFRAME=M15

SECOND_PRODUCER_PROVEN=YES
LEGACY_ANDROID_RUNTIME=STOPPED
LEGACY_ANDROID_KNOWN_RESTART_PATH=DISABLED
FRESH_TERMUX_SESSION_TEST=PASS
PHONE_REBOOT_TEST=NOT_YET_RUN

SUPABASE_KEY_TYPE=MODERN_SB_SECRET
PHONE_AND_HETZNER_SUPABASE_KEY_FINGERPRINT=MATCH
PROFITLAB_EDGE_FUNCTION_SERVICE_ROLE_PATH=SEPARATE
SUPABASE_ROTATION_AUTHORIZED=NO

TELEGRAM_CONSUMER_INVENTORY=INCOMPLETE
TELEGRAM_ROTATION_AUTHORIZED=NO

RECENT_LEDGER_PROVENANCE=CROSS_CONTAMINATED
11_NOV_WIN_HETZNER=NO
12_NOV_CANCEL_HETZNER=NO
23_NOV_USDJPY_HETZNER_CLUSTER=6_LOSSES_-131.6_PIPS

D1_CONFIRMATION_READER_PATH_DEFECT=VERIFIED
D1_REPAIR_DEPLOYED=NO
ONE_ACTIVE_PAIR_DIRECTION_CONTROL_DEPLOYED=NO

STRATEGY_TUNING=NO
PAIR_CHANGES=NO
TIMEFRAME_CHANGES=NO
PRODUCTION_CHANGE_AUTHORIZED=NO

CURRENT_PHASE=RETIRE_LEGACY_PRODUCER_AND_ESTABLISH_SINGLE_PRODUCER_TRUTH
NEXT_ACTION=AUTHORIZE_CONTROLLED_SUPABASE_SECRET_ROTATION
FOUNDER_APPROVAL_REQUIRED=YES
FURTHER_BROAD_AI_REVIEW=STOP
```

Canonical record: `CONTINUITY_CURRENT.md`.

## Critical producer correction

Do not repeat the old claim that Android was only a control/observation device.

A live Termux BotA runtime was proven on 24 Nov 2026. It was making Romanian-origin Supabase requests and could create/close production signal rows.

Do not repeat the old clean post-release sequence `LOSS -> WIN -> CANCELLED`.

The 11 Nov EURUSD +20.8 winner was created by the Romanian legacy producer, not Hetzner. The 12 Nov GBPUSD cancellation was also performed by the Romanian legacy producer.

The Supabase ledger is mixed-producer evidence and cannot be treated as a clean strategy sample.

## Legacy-phone retirement status

Verified:

- BotA runit services on phone were stopped.
- The watchdog was killed.
- The known Termux session launcher was made non-executable.
- A newly opened Termux session did not restart BotA.
- `pgrep` returned `NO_BOTA_PROCESSES_PASS`.
- `bota-closer` and `bota-supervisor` remained down.
- Supabase showed no Romanian use of the shared BotA key from shutdown through 16:00 UTC.

Not yet verified:

- persistence across a phone reboot;
- credential revocation;
- absence of every possible alternate launch mechanism.

Treat the phone as **stopped but still credential-capable** until the shared Supabase key is revoked.

## Credential inventory result

### Supabase

The inventory is sufficient to plan a dedicated Supabase rotation:

- Hetzner uses a modern `sb_secret_...` key.
- Supabase log fingerprints prove the phone and Hetzner use the same key.
- Current post-shutdown logs show that key only from Hetzner.
- ProfitLab/Stripe Edge Functions use the separate legacy `SUPABASE_SERVICE_ROLE_KEY` path.
- GitHub Actions does not inject a production Supabase secret.
- No BotA/ProfitLab Vercel project is present in the connected Vercel account.

Do not rotate the project JWT secret. Rotate only the modern BotA secret after explicit founder approval.

### Telegram

Do not rotate Telegram yet.

Hetzner uses `TELEGRAM_BOT_TOKEN`.

The active Supabase `send-telegram` function also has a Telegram bot token, but sends to an admin chat and had no invocation in the last checked 24 hours.

The dividend scanner uses `TELEGRAM_TOKEN`.

Exact token identity across these consumers is still unverified.

## Current production defects / risks

### D1 confirmation

The D1 cache writer uses `BOTA_MUTABLE_ROOT` and writes under `/var/lib/bota/cache`.

The scoring reader uses `ROOT` / `BOTA_ROOT` semantics and silently returns `ANY` when its path is missing.

Production has valid D1 cache state, but the scorer was not reading it.

Future repair: use the mutable-root cache and fail closed / alert if unavailable.

Not deployed.

### Correlated exposure

On 23 Nov Hetzner created six overlapping USDJPY BUY signals and they lost a combined -131.6 pips.

A one-ACTIVE-per-pair+direction control is a candidate repair, but it must be replayed across history before authorization so removed winners are counted too.

Not deployed.

## Strategy boundary

Preserve:

```text
POLICY_B_ACCEPTED=195
PRE_REGISTERED_KILL_THRESHOLD=400
HISTORICAL_CORPUS_GATE=FAIL
STRATEGY_EDGE_VALIDATED=NO
```

Do not tune strategy from the contaminated live ledger.

## Exactly one current action

Obtain explicit founder approval for the controlled **Supabase BotA secret rotation only**.

Do not bundle Telegram rotation, D1 repair, exposure-control changes, strategy tuning or provider changes into that action.
