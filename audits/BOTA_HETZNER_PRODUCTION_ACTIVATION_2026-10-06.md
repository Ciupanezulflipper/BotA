# BotA Hetzner Production Activation — 2026-10-06

Status: **DEPLOYMENT COMPLETE / RUNTIME ACTIVE / DUAL-SINK DELIVERY ARMED BUT NOT YET OBSERVED ON A QUALIFIED SIGNAL**

## Scope

This record captures the exact Hetzner production activation and immediate post-activation evidence for BotA on 2026-10-06 UTC.

No strategy parameters, pair scope, timeframe scope, or live-money trading authority were changed.

## Exact deployed release

```text
PREVIOUS_RELEASE=d81c0a3da3363089ed200e264ae066fdf15fb5ba
DEPLOYED_RELEASE=4424518e7b42ecf2a070967d626a9ac86bf04d53
DEPLOYED_TREE=9e76b0b37012a2276cd36301e3e7267b1b6674d8
DEPLOYMENT_ID=60de921f-1020-4e55-b6ff-0b03d3548e63
DEPLOYMENT_PHASE=COMPLETE
DEPLOYMENT_HEALTHY=true
ROLLBACK_USED=NO
TARGET_RUNTIME_INSTANCE_ID=71c3cc1e-a1be-4bc6-8a23-3738eb70ba35
```

Immediate service proof:

```text
CURRENT=/opt/bota/releases/4424518e7b42ecf2a070967d626a9ac86bf04d53
SERVICE_ACTIVE=active
SERVICE_ENABLED=enabled
MAINPID=4104125
```

## Credential and live-delivery contract

The production-scoped credential source is:

```text
/etc/bota/live-delivery.env
MODE=600
OWNER=bota
GROUP=bota
```

Only key presence and value lengths were inspected; secret values are intentionally excluded from repository evidence.

Candidate runtime contract proof:

```text
LIVE_DELIVERY_CONTRACT=PASS
```

The parent R5 runtime remains shadowed/fail-closed. Approved child jobs receive only their scoped live credentials. This is intentional and must not be misread as the whole deployment being delivery-disabled.

## Provider/lifecycle state

The forward provider contract is Yahoo.

Immediate post-deploy runtime evidence showed fresh Yahoo cache/candle/indicator updates for EURUSD, GBPUSD and USDJPY, including M15/H1/H4/D1 data. Provider accounting files also advanced.

Signal closer proof at 08:45 UTC:

```text
provider=yahoo
Found 0 ACTIVE signals to evaluate
TELEGRAM retry scan candidates=0 sent=0 skipped=0
closed=0
cancelled=0
still_open=0
dry_run=False
```

No pending historical Telegram closure retry files were present before activation.

## Watcher evidence after activation

The watcher completed natural market-open cycles at 08:45, 08:50 and 08:55 UTC.

All three pairs were evaluated each cycle:

- EURUSD M15
- GBPUSD M15
- USDJPY M15

The sampled cycles completed with:

```text
run_rc=0
terminal_outcome=EVALUATED_REJECTED
```

The strategy rejected every sampled candidate. Examples:

- EURUSD: direction not tradeable / score below threshold / invalid entry / non-positive RR / macro gate
- GBPUSD: same broad rejection family
- USDJPY: score below threshold / macro gate

For these rejected decisions the ledger correctly recorded:

```text
telegram_result=not_attempted
supabase_result=not_attempted
```

This is expected: no qualified signal existed to deliver.

## ProfitLab delivery worker

The durable ProfitLab delivery cursor advanced after activation and was caught up to the source at the sampled checkpoint:

```json
{"offset": 2896918, "schema_version": "1.0", "source_size": 2896918}
```

This proves the worker is progressing and has no backlog at that checkpoint. It does **not** prove a new post-activation qualified signal has been published to Supabase.

## Current answer

```text
BOTA_LIVE_ON_HETZNER=YES
BOTA_SERVICE_ACTIVE=YES
BOTA_SERVICE_ENABLED_24_7=YES
THREE_PAIR_M15_SCANNING=YES
MARKET_DATA_REFRESHING=YES
PROVIDER_CONTRACT=YAHOO
SIGNAL_CLOSER_RUNNING=YES
PROFITLAB_DELIVERY_WORKER_PROGRESSING=YES
TELEGRAM_CREDENTIAL_VALIDATED=YES
SUPABASE_SERVICE_CREDENTIAL_VALIDATED=YES
DUAL_SINK_CREDENTIAL_CONTRACT=PASS

REAL_TELEGRAM_SIGNAL_POST_ACTIVATION=NOT_YET_OBSERVED
REAL_PROFITLAB_SIGNAL_POST_ACTIVATION=NOT_YET_OBSERVED
REASON=NO_QUALIFIED_SIGNAL_OCCURRED_IN_SAMPLED_POST_ACTIVATION_CYCLES
```

Therefore BotA is live and scanning on Hetzner. The Telegram and ProfitLab delivery paths are configured, credential-valid and armed, but a real end-to-end signal delivery has not yet been empirically observed after this activation because the strategy has not produced a qualifying signal.

## Safety boundaries unchanged

```text
BOTA_EDGE_STATUS=UNVALIDATED
LIVE_MONEY_TRADING=NO
STRATEGY_TUNING=NO
PAIR_CHANGES=NO
TIMEFRAME_CHANGES=NO
FORCED_PRODUCTION_SIGNAL=NO
```

## Next acceptance proof

Obtain one bounded end-to-end dual-sink delivery proof without changing strategy. Prefer a supported non-trading delivery smoke test if an existing repository path allows it; otherwise observe the next natural qualified signal. Do not manufacture or force a production trading signal solely to satisfy the acceptance check.
