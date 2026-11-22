# BotA Chat Handoff

Last updated: **2026-11-22 UTC**

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
ANDROID_ACTIVE_SCANNER=NO

PR135_RECONCILIATION=MERGED
PR136_GREEN_VISIBILITY_FIX=MERGED_AND_DEPLOYED

NATURAL_GREEN_LIFECYCLE=PROVEN
POST_83FA_RESULTS=LOSS,WIN,CANCELLED
POST_83FA_CLOSED_NET=-1.7_PIPS
POST_83FA_SAMPLE_TOO_SMALL_FOR_STRATEGY_CHANGE=YES

REPORTING_ACCOUNTING_CONSISTENCY=OPEN
SCAN_DELAY_CLASSIFICATION=OPEN
API_USAGE_COUNTER_ACCURACY=OPEN

CURRENT_PHASE=OBSERVE_STORE_COLLECT_ANALYZE
STRATEGY_TUNING=NO
PRODUCTION_CHANGE_AUTHORIZED=NO
NEXT_ACTION=READ_ONLY_REPORTING_AND_HEALTH_ACCOUNTING_RECONCILIATION
```

Canonical record: `CONTINUITY_CURRENT.md`.

## Verified current production evidence

`/opt/bota/current` resolves to release `83fa71e651483c95096ce635b525cacbf91cbc5d`.

Post-release natural GREEN lifecycles:

```text
04 Nov USDJPY BUY  158.42101 -> LOSS -22.5
11 Nov EURUSD SELL 1.11410   -> WIN  +20.8
12 Nov GBPUSD SELL 1.32456   -> CANCELLED 0.0 after ~24h
```

Supabase signal snapshot on 22 Nov:

```text
CLOSED=67
WINS=24
LOSSES=43
CANCELLED=8
ACTIVE=0
CLOSED_NET_PIPS=+34.6
CLOSED_WIN_RATE=35.8%
```

Signal-ledger statistics are not brokerage-account P&L.

## Open blocker

The production trading lifecycle works, but monitoring/accounting reports conflict:

- 11 Nov daily summary reports zero qualified/Telegram despite the real EURUSD GREEN WIN.
- 12 Nov daily summary and Proof-of-Work disagree on accepted/eligible counts; production proves one GREEN plus one YELLOW watchlist.
- API usage was reported as high as `960/800 (120%)`.
- 18-20 Nov generated multi-hour scan-delay/restored warnings even though final market-open daily reports still showed 156 cycles.

Do not label zero-signal days as strategy evidence until the report-window/definition and delay-classification issues are reconciled.

## Strategy boundary

No change to Policy B, score/ADX/RSI thresholds, pairs, timeframe, H1 confirmation, TP/SL or provider policy. Three post-release GREEN lifecycles are not a sufficient strategy sample.

## Exactly one next action

Perform one bounded read-only reconciliation of Daily Market Report, Proof-of-Work, Telegram delivery, Supabase `public.signals`, API usage accounting and scan-delay classification. No production mutation is included.