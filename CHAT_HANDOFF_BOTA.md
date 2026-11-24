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
LEGACY_CREDENTIALS_REVOKED=NO

RECENT_SIGNAL_LEDGER=MIXED_PRODUCERS
11_NOV_EURUSD_WIN=LEGACY_PHONE_CREATED
12_NOV_GBPUSD_CANCEL=LEGACY_PHONE_PERFORMED
23_NOV_USDJPY_HETZNER_CLUSTER=6_LOSSES_TOTAL_-131.6

D1_READER_WRITER_PATH_MISMATCH=VERIFIED
D1_REPAIR_DEPLOYED=NO
ONE_ACTIVE_PAIR_DIRECTION_CONTROL_DEPLOYED=NO

STRATEGY_TUNING=NO
PRODUCTION_CHANGE_AUTHORIZED=NO
NEXT_ACTION=READ_ONLY_CREDENTIAL_CONSUMER_INVENTORY
```

Canonical record: `CONTINUITY_CURRENT.md`.

## What was discovered

The Android/Termux installation was still an active legacy BotA producer.

Phone-side closer timestamps matched Romanian/Vodafone Supabase traffic. That proves the phone was still touching the production signal ledger.

It was not safe to continue treating every recent Supabase row as Hetzner evidence.

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
7. Supabase showed no Romanian edge traffic through 14:30 UTC after shutdown.

This is strong shutdown proof.

It is not yet permanent-retirement proof because the old credentials still exist and no reboot test has been performed.

## Current blocker

Do not rotate credentials yet.

The Supabase credential type and consumer list are unknown. A blind rotation could break ProfitLab, Stripe webhook processing, subscriber login/session behavior or another legitimate service.

The next phase must inventory consumers first, using prefixes/fingerprints only and never printing full credentials.

## Other verified production issues

- D1 state is written to the mutable cache but the scorer reads a different root and silently falls back to `ANY`.
- Hetzner allowed six simultaneous same-pair/same-direction USDJPY GREEN positions on 23 Nov.
- Yahoo is the current Hetzner candle provider; local API-warning counters are not proof of Twelve Data billing usage.

Do not fix these in the credential-inventory step.

## Strategy boundary

The live ledger is contaminated by multiple producers and generations. It is not a clean strategy-validation dataset.

Do not change Policy B, score/ADX/RSI thresholds, pair scope, timeframe, TP/SL or provider policy from this evidence.

## Exactly one next action

Perform one bounded read-only credential consumer inventory covering:

- Hetzner Supabase key type/prefix;
- ProfitLab and Stripe webhook dependencies;
- Supabase Edge Functions;
- GitHub Actions secret references;
- laptop/WSL copies;
- Telegram bot-token consumers.

No mutation is authorized as part of this step.
