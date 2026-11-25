# BotA Chat Handoff

Last updated: **2026-11-24 UTC**

Read this first in a new AI session before proposing BotA work.

## Current grounded answer

```text
BOTA_EDGE_STATUS=UNVALIDATED
LIVE_MONEY_TRADING=NO

PRIMARY_RUNTIME=HETZNER
CURRENT_HETZNER_RUNTIME_STATE=ACTIVE
DEPLOYED_RELEASE=83fa71e651483c95096ce635b525cacbf91cbc5d
PROVIDER=YAHOO
PAIRS=EURUSD,GBPUSD,USDJPY
TIMEFRAME=M15

LEGACY_ANDROID_PRODUCER_PROVEN=YES
LEGACY_ANDROID_RUNTIME=STOPPED
KNOWN_TERMUX_RESTART_PATH=DISABLED
FRESH_SESSION_RESTART_TEST=PASS
PHONE_REBOOT_TEST=NOT_YET_RUN

SUPABASE_KEY_TYPE=MODERN_SB_SECRET
PHONE_AND_HETZNER_SUPABASE_KEY_FINGERPRINT=MATCH
PROFITLAB_SERVICE_ROLE_PATH=SEPARATE
SUPABASE_ROTATION_AUTHORIZED=NO

TELEGRAM_CONSUMERS_FULLY_RECONCILED=NO
TELEGRAM_ROTATION_AUTHORIZED=NO

RECENT_SIGNAL_LEDGER=MIXED_PRODUCERS
11_NOV_EURUSD_WIN=LEGACY_PHONE_CREATED
12_NOV_GBPUSD_CANCEL=LEGACY_PHONE_PERFORMED
23_NOV_USDJPY_HETZNER_CLUSTER=6_LOSSES_TOTAL_-131.6

D1_READER_WRITER_PATH_MISMATCH=VERIFIED
D1_REPAIR_DEPLOYED=NO
ONE_ACTIVE_PAIR_DIRECTION_CONTROL_DEPLOYED=NO

STRATEGY_TUNING=NO
PRODUCTION_CHANGE_AUTHORIZED=NO
NEXT_ACTION=AUTHORIZE_CONTROLLED_SUPABASE_SECRET_ROTATION
FOUNDER_APPROVAL_REQUIRED=YES
```

Canonical record: `CONTINUITY_CURRENT.md`.

## What was discovered

The Android/Termux installation was still an active legacy BotA producer.

Phone-side closer timestamps matched Romanian-origin Supabase traffic. The phone was therefore still touching the production signal ledger.

Most important provenance corrections:

- 11 Nov EURUSD SELL +20.8: created by legacy phone, not Hetzner.
- 12 Nov GBPUSD: created by Hetzner, later cancelled by legacy phone.
- 23 Nov USDJPY: six overlapping BUY signals were created by Hetzner and all lost, total -131.6 pips.

## Retirement progress

On 24 Nov:

1. The phone watchdog was stopped first.
2. BotA phone services were put down.
3. The watchdog launcher was made non-executable.
4. A fresh Termux session was opened.
5. No BotA/watchdog process returned.
6. `bota-closer` and `bota-supervisor` remained down.
7. Supabase showed no Romanian use of the shared BotA key through 16:00 UTC after shutdown.

This is strong shutdown proof.

It is not yet permanent-retirement proof because the shared Supabase secret is still valid and the phone has not been reboot-tested after revocation.

## Credential inventory result

The earlier rotation blocker is substantially resolved for Supabase.

Verified:

- Hetzner uses a modern independently rotatable `sb_secret_...` key.
- Supabase API-key fingerprints prove the legacy phone and Hetzner used the exact same key.
- In the checked 24-hour usage window that key appeared from Hetzner and Romanian residential/mobile networks; after shutdown only Hetzner remained.
- ProfitLab/Stripe Supabase Edge Functions use the separate legacy `SUPABASE_SERVICE_ROLE_KEY`, not Hetzner's `SUPABASE_SERVICE_KEY`.
- GitHub Actions does not inject a live BotA Supabase key.
- The connected Vercel account contains LifVio projects only; no ProfitLab/BotA Vercel project is present.
- A laptop file named `C:\Users\tomag\Supabase key.txt` contains a modern secret key, but exact equality with the live BotA key was not extracted or proven.

Therefore a dedicated rotation of the modern BotA Supabase key is the correct next production step, subject to explicit approval.

## Telegram remains separate

Do not rotate Telegram in the Supabase step.

- Hetzner uses `TELEGRAM_BOT_TOKEN`.
- Supabase has an active admin-only `send-telegram` function with its own Telegram bot-token environment variable.
- No invocation of that Edge Function was found in the last checked 24 hours.
- The dividend scanner uses `TELEGRAM_TOKEN`.
- Exact token identity across these consumers is not yet proven.

Telegram retirement must be handled as a separate bounded change.

## Other verified production issues

- D1 state is written to the mutable cache but the scorer reads a different root and silently falls back to `ANY`.
- Hetzner allowed six simultaneous same-pair/same-direction USDJPY GREEN positions on 23 Nov.
- Yahoo is the current Hetzner candle provider; local API-warning counters are not proof of Twelve Data billing usage.

Do not fix these in the credential-rotation step.

## Strategy boundary

The live ledger is contaminated by multiple producers and generations. It is not a clean strategy-validation dataset.

Do not change Policy B, score/ADX/RSI thresholds, pair scope, timeframe, TP/SL or provider policy from this evidence.

## Exactly one next action

Obtain explicit founder approval for a controlled **Supabase BotA secret rotation only**:

1. create a replacement modern secret dedicated to Hetzner BotA;
2. configure Hetzner only;
3. verify Hetzner uses the new fingerprint;
4. revoke the old shared key;
5. verify the retired key cannot authenticate;
6. reboot the phone during the verification window and check for rejected legacy attempts.

Do not rotate Telegram or make strategy/code repairs in the same action.
