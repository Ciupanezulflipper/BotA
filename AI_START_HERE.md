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
LEGACY_CREDENTIALS_REVOKED=NO

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
NEXT_ACTION=READ_ONLY_CREDENTIAL_CONSUMER_INVENTORY
FURTHER_BROAD_AI_REVIEW=STOP
```

Canonical record: `CONTINUITY_CURRENT.md`.

## Critical correction to prior handoffs

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
- Supabase showed zero Romanian edge requests from the shutdown point through 14:30 UTC.

Not yet verified:

- persistence across a phone reboot;
- credential revocation;
- absence of every possible alternate launch mechanism;
- complete credential dependency map.

Treat the phone as **stopped but still credential-capable**, not permanently retired.

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

## Credential-rotation safety boundary

Do not rotate Supabase or Telegram credentials blindly.

First identify all consumers.

A shared Supabase service credential may be used by ProfitLab, Stripe webhook processing, Edge Functions, GitHub Actions or another runtime. Breaking one of those can harm subscribers.

Do not print or store full secrets. Compare only safe prefixes/fingerprints.

A final clean-producer verification window starts only after a safe credential migration and active rejection tests, with legitimate ProfitLab/Vercel writes distinguished from unauthorized writes.

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

Run one read-only credential consumer inventory.

No code change, deployment, credential rotation, phone reboot, strategy tuning or provider change is included in that action.
