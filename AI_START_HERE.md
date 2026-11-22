# BotA AI Start Here

Last updated: **2026-11-22 UTC**

Read this before proposing BotA strategy, deployment, Telegram, ProfitLab, Android/Termux, VPS/Hetzner, replay, historical-data or runtime work.

## Current authoritative truth

```text
PROJECT=BotA
BOTA_EDGE_STATUS=UNVALIDATED
LIVE_MONEY_TRADING=NO
PRIMARY_RUNTIME=HETZNER
CURRENT_HETZNER_RUNTIME_STATE=ACTIVE
DEPLOYED_RELEASE=83fa71e651483c95096ce635b525cacbf91cbc5d
PROVIDER=YAHOO
PAIRS=EURUSD,GBPUSD,USDJPY
TIMEFRAME=M15
ANDROID_ACTIVE_SCANNER=NO

PR135=MERGED
PR136=MERGED
DISTINCT_GREEN_TELEGRAM_VISIBILITY_FIX=LIVE

NATURAL_GREEN_TO_TELEGRAM=PROVEN
NATURAL_GREEN_TO_SUPABASE=PROVEN
NATURAL_CLOSURE_WIN_LOSS=PROVEN
NATURAL_24H_CANCEL=PROVEN

POST_83FA_GREEN_LIFECYCLES=3
POST_83FA_CLOSED=2
POST_83FA_WINS=1
POST_83FA_LOSSES=1
POST_83FA_CANCELLED=1
POST_83FA_NET_CLOSED_PIPS=-1.7

REPORTING_ACCOUNTING_CONSISTENCY=OPEN
SCAN_DELAY_CLASSIFICATION=OPEN
API_USAGE_COUNTER_ACCURACY=OPEN

STRATEGY_TUNING=NO
PAIR_CHANGES=NO
TIMEFRAME_CHANGES=NO
FORCED_SIGNAL_GENERATION=NO
PRODUCTION_CHANGE_AUTHORIZED=NO

CURRENT_PHASE=OBSERVE_STORE_COLLECT_ANALYZE
NEXT_ACTION=READ_ONLY_REPORTING_AND_HEALTH_ACCOUNTING_RECONCILIATION
FURTHER_BROAD_AI_REVIEW=STOP
```

Canonical current record: `CONTINUITY_CURRENT.md`.

Historical production activation baseline: `audits/BOTA_HETZNER_PRODUCTION_ACTIVATION_2026-10-06.md`.

## What changed since the October handoff

PR #135 reconciled the production lineage into `main` on 2 Nov 2026.

PR #136 then fixed the 30 Oct lifecycle inconsistency: distinct GREEN signals bypass the broad pair/timeframe Telegram cooldown; YELLOW/watchlist cooldown and exact identity dedup remain unchanged. Its merge commit `83fa71e65148...` is the currently deployed production release.

The previous instruction to wait for the first natural GREEN is obsolete. Natural post-release GREEN lifecycle evidence now exists.

## Verified post-release lifecycles

```text
2026-11-04 USDJPY BUY  158.42101 -> LOSS      -22.5 pips
2026-11-11 EURUSD SELL 1.11410   -> WIN       +20.8 pips
2026-11-12 GBPUSD SELL 1.32456   -> CANCELLED  0.0 pips after ~24h
```

Three lifecycles are insufficient to judge strategy edge. Do not tune thresholds from this sample.

## Current reporting blocker

Do not assume all daily summary counters are internally consistent.

- 11 Nov Daily Market Report says `0 qualified / 0 Telegram`, but production proves a real GREEN EURUSD SELL and +20.8 pip WIN.
- 12 Nov Daily Market Report says `2 qualified / 2 Telegram`, while Proof-of-Work says `0 filter-accepted / 0 eligible`; production proves one GREEN trade plus one YELLOW watchlist.
- Proof-of-Work reported API use above the nominal daily limit, and later multi-hour `SCAN DELAYED` warnings self-restored while full daily 156-cycle counts were still reported.

Root cause is not yet proven. Treat this as a reporting/health-accounting audit, not a strategy defect.

## Current runtime health

On 22 Nov 2026 Supabase reported `bota-hetzner-primary` as `HEALTHY` with no current failure reason. The date is Sunday / market closed.

## Historical corpus boundary

Preserve the prior frozen historical research result:

```text
POLICY_B_ACCEPTED=195
PRE_REGISTERED_KILL_THRESHOLD=400
HISTORICAL_CORPUS_GATE=FAIL
STRATEGY_EDGE_VALIDATED=NO
```

Do not reinterpret the current three live lifecycles as reopening or invalidating the historical corpus protocol.

## Exactly one current action

Run one bounded read-only reconciliation of Daily Market Report, Proof-of-Work, Telegram, Supabase signal lifecycle, API-usage counters and scan-delay classification. No strategy or production change is part of that action.