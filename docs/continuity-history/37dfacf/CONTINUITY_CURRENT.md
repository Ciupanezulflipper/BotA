# BotA Current Continuity State

Last updated: **2026-11-24 UTC**

This is the canonical operational handoff. Historical audits remain evidence; stale current-state instructions are superseded by this file.

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
PHONE_REBOOT_TEST=NOT_YET_RUN

SUPABASE_KEY_TYPE=MODERN_SB_SECRET
PHONE_AND_HETZNER_SUPABASE_KEY_FINGERPRINT=MATCH
SUPABASE_EDGE_FUNCTIONS_USE_SEPARATE_LEGACY_SERVICE_ROLE_PATH=YES
SUPABASE_ROTATION_BLAST_RADIUS=BOUNDED_ENOUGH_TO_PLAN
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
```

## What changed on 2026-11-24

A second BotA producer was proven on the Android/Termux phone.

The phone was not merely a control/observation device. It had active runit BotA services and a watchdog capable of reviving them. Supabase edge logs matched phone-side closer timestamps to Romanian-origin requests, proving that the legacy phone runtime was still touching the production signal ledger.

The legacy runtime was then stopped. Its known Termux-session watchdog launcher:

```text
~/BotA/tools/start_native_service_daemon_watchdog.sh
```

was made non-executable.

A fresh Termux session was opened afterwards and verified:

```text
NO_BOTA_PROCESSES_PASS
bota-closer=down
bota-supervisor=down
```

Supabase verification from the shutdown point through **2026-11-24 16:00 UTC** showed the shared BotA key being used only from Hetzner. No Romanian use of that key returned in the checked post-shutdown window.

A phone reboot has not yet been used as a persistence test.

## Credential inventory — resolved facts

The read-only credential inventory materially narrowed the retirement risk.

### Supabase

Verified:

- Hetzner live delivery reads its credentials from `/etc/bota/live-delivery.env`.
- Hetzner uses a modern independently rotatable `sb_secret_...` key for `SUPABASE_SERVICE_KEY`.
- Hetzner does **not** carry `SUPABASE_SERVICE_ROLE_KEY` in that live-delivery file.
- Supabase request logs expose a safe API-key fingerprint.
- Romanian legacy-phone requests and Hetzner requests used the **same exact Supabase API-key fingerprint**.
- A 24-hour fingerprint sweep showed that key used by Hetzner and Romanian residential/mobile origins; no third active origin class was observed.
- After the phone shutdown, the same key fingerprint was observed only from Hetzner through 16:00 UTC.

This resolves the key question: revoking that modern BotA secret will lock the legacy phone out of Supabase while a replacement key can be provisioned for Hetzner.

### ProfitLab / Stripe / Supabase Edge Functions

Active Supabase Edge Functions include ProfitLab and billing functions such as:

- `stripe-webhook`
- `create-checkout`
- `check-subscription`
- `customer-portal`
- `get-signals`
- `sync-status`
- `update-preferences`
- `bota-health-admin`
- `send-telegram`

The ProfitLab/admin functions that need privileged database access read the separate legacy `SUPABASE_SERVICE_ROLE_KEY` environment variable. They do not read BotA's Hetzner `SUPABASE_SERVICE_KEY`.

Current Supabase documentation confirms that modern `sb_secret_...` keys can be created and revoked independently from the legacy JWT-based `service_role` key.

Therefore rotating the modern Hetzner/phone BotA key should **not** require rotating the project JWT secret and should not, by itself, log out ProfitLab subscribers or break the Edge Function service-role path.

### GitHub Actions

Repository search found one workflow that mentions `SUPABASE_SERVICE_KEY`:

```text
.github/workflows/historical-candle-acquisition.yml
```

It explicitly sets the value to an empty string for an offline/no-network validation job.

No GitHub Actions workflow reference to `secrets.*` was found for BotA.

GitHub Actions is therefore not an active consumer of the production BotA Supabase key based on current repository evidence.

### Vercel

The connected Vercel account exposes only LifVio projects. No ProfitLab/BotA Vercel project is present in the connected project list.

The Vercel connector returns 403 for environment-variable metadata and the local Vercel CLI is unavailable, so accidental storage of a BotA key inside a LifVio environment remains unverified. There is no current evidence that LifVio consumes the BotA key.

### Laptop copies

A local file exists:

```text
C:\Users\tomag\Supabase key.txt
```

It contains a modern `sb_secret_...` value. The exact value was not extracted into chat. Whether it is the same current BotA key remains unverified because the local tooling correctly blocked raw-secret fingerprint extraction.

No `.env.runtime` or `strategy.env` file was found in the primary checked BotA laptop package. Broader home-directory searches were time-bounded and may be incomplete.

The laptop copy is a credential-hygiene concern, but no laptop BotA runtime was found during the earlier runtime audit.

### Telegram

Hetzner has `TELEGRAM_BOT_TOKEN` in its live-delivery secret file.

The Supabase `send-telegram` Edge Function also uses a `TELEGRAM_BOT_TOKEN`, but its code sends to `TELEGRAM_ADMIN_CHAT_ID` and requires admin authorization. No invocation of that function was found in the last checked 24-hour log window.

The dividend-capture scanner uses a separate environment variable name, `TELEGRAM_TOKEN`, and the laptop copy of that repository contains no live `.env` file.

Exact Telegram-token identity across Hetzner, Supabase Edge Functions, the phone, and the dividend scanner is still unverified.

Therefore: **do not rotate Telegram yet**.

## Producer-lineage correction

Previous continuity documents incorrectly treated all recent Supabase rows as Hetzner production evidence.

Verified examples:

- **2026-11-11 EURUSD SELL +20.8 pips:** created by the Romanian legacy producer, not by Hetzner. Hetzner's own pipeline at the matching time recorded HOLD/filter rejection.
- The same 11 Nov row was later touched by both the Hetzner closer and the Romanian legacy closer.
- **2026-11-12 GBPUSD SELL:** created by Hetzner, but its later cancellation was performed by the Romanian legacy producer.
- **2026-11-23 USDJPY:** six GREEN M15 BUY rows were created by Hetzner and all closed as losses, total **-131.6 pips**.

Therefore the earlier summary:

```text
LOSS -> WIN -> CANCELLED
```

must not be used as a clean Hetzner strategy sample.

The stored Supabase ledger contains mixed producers and mixed generations. It is operational evidence, not a clean strategy-validation corpus.

## 23 Nov correlated exposure event

Hetzner created six USDJPY M15 BUY signals between 14:15 and 16:30 UTC on 23 Nov.

Results:

```text
-20.5
-22.5
-22.4
-21.6
-21.7
-22.9
TOTAL=-131.6 pips
```

They represented one highly correlated thesis repeatedly re-entered while earlier signals were still active.

A one-ACTIVE-per-pair+direction rule is a candidate exposure-control repair, but it is **not yet authorized or deployed**. It must be replayed against historical episodes so removed winners are counted as well as removed losses.

## D1 confirmation defect

A production path mismatch was verified.

The D1 cache writer stores mutable state under:

```text
/var/lib/bota/cache
```

using `BOTA_MUTABLE_ROOT`.

The scoring reader instead derives its D1 cache path from `ROOT` / `BOTA_ROOT`, falling back to `~/BotA`, and silently degrades to:

```text
d1_trend=ANY
```

when the expected file is absent.

Production has valid D1 cache files under `/var/lib/bota/cache`, but the live scoring reader was not reading that location. Recent GREEN signals therefore showed D1 as `ANY`.

The correct future repair is to read mutable D1 state from `BOTA_MUTABLE_ROOT` and fail closed / alert when D1 state is unavailable.

No D1 repair is deployed yet.

## Provider / warning correction

Hetzner production is frozen to Yahoo for candle acquisition.

The prior `600/800` / `960/800` style warnings were generated by a generic local counter and are not proof of actual Twelve Data billing usage.

Current Hetzner provider accounting showed no Twelve Data production calls during the audit.

Do not purchase additional market-data quota based on those warnings.

## Retirement boundary

The phone runtime is stopped, but retirement is not yet permanent because the shared Supabase key remains valid.

The key inventory now shows that the Supabase rotation can be separated from Telegram rotation.

Recommended controlled Supabase sequence after explicit approval:

1. Create a new named modern secret key dedicated to Hetzner BotA.
2. Configure only Hetzner to use the replacement key.
3. Restart/verify BotA and confirm Supabase requests use the new key fingerprint.
4. Revoke the old shared BotA secret.
5. Verify the old fingerprint can no longer authenticate.
6. Reboot the phone inside the verification window and watch for rejected legacy attempts or process resurrection.
7. Begin the final clean-producer observation window at the credential-revocation/verification boundary.

Do not change Telegram credentials in the same step.

## Final clean-producer acceptance

The final acceptance window has not started.

At minimum it must show:

- old BotA Supabase secret revoked;
- Hetzner operating on the replacement secret;
- no successful use of the retired key;
- no unexplained non-Hetzner BotA writes;
- phone reboot performed inside the window;
- at least one real Hetzner signal lifecycle created and closed during the window;
- Telegram output reconciled separately against Hetzner send records.

Legitimate ProfitLab Edge Function traffic uses a different credential path and must not be misclassified as rogue BotA traffic.

## Strategy boundary

Do not tune Policy B, indicator weights, ADX/RSI thresholds, pairs, timeframe, TP/SL, news scoring or provider policy from the contaminated ledger.

Historical research boundary remains:

```text
POLICY_B_ACCEPTED=195
PRE_REGISTERED_KILL_THRESHOLD=400
HISTORICAL_CORPUS_GATE=FAIL
STRATEGY_EDGE_VALIDATED=NO
```

The immediate problem remains producer integrity and exposure control, not strategy optimization.

## Exactly one next action

Obtain explicit founder approval for the **controlled Supabase secret rotation only**.

Do not rotate Telegram in the same change.

No D1 repair, exposure-control repair, strategy tuning, provider change or other production mutation belongs in that step.
