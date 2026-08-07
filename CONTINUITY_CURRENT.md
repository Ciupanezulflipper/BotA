# BotA Current Continuity State

Last updated: 2026-08-07 18:58 UTC

## Authoritative identifiers

```text
RECORDED_DATE=2026-08-07
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=73b2306b5843f3396823ce815e96051abf78cf50
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_SERVICE_DAEMON_PIDFILE=31140
```

## Runtime state

```text
manager_count=1
manager_pid=31140
required=7
owned=6
running=7
orphaned=1
duplicate_service_rows=0
healthy=false
orphan_service=crond
```

The watcher is live. Runtime ownership remains degraded but is not the current signal-quality root cause.

## Current effective settings

```text
PAIRS=EURUSD GBPUSD
TIMEFRAMES=M15
FILTER_SCORE_MIN=65
FILTER_SCORE_MIN_ALL=65
H1_TREND_MIN_SCORE=40
H1_VETO_OVERRIDE_SCORE=75
H1_VETO_OVERRIDE_ADX=40
TELEGRAM_MIN_SCORE=70
TELEGRAM_TIER_YELLOW_MIN=70
TELEGRAM_TIER_GREEN_MIN=75
TELEGRAM_COOLDOWN_SECONDS=1800
DRY_RUN_MODE=0
TELEGRAM_ENABLED=1
```

Only two pairs are live.

## Strategy funnel

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 524 survive score
  -> 410 rejected by H1-neutral veto
  -> 114 survive H1
  -> 4 rejected by H4+D1 opposition
  -> 110 strategy-accepted
```

## Accepted -> Telegram funnel

```text
61 sent
38 cooldown-suppressed
6 Telegram score-gated
1 send failure
```

Four of the 110 accepted CSV rows remain delivery-unknown.

## Recent delivered-signal quality

Read-only Supabase evidence for BotA M15 signals created on or after 2026-06-01:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
75-84_TOTAL_PIPS=-36.40
85+_TOTAL_PIPS=-35.00
```

Recent high scores are not reliably separating winners from losers.

## March component/outcome evidence

```text
LEDGER_ROWS=51
JOINED=51
WINS=13
LOSSES=38
TOTAL_PIPS=-264.1
ADX<30: N=17 W=9 L=8 PIPS=+98.0
SCORE>=70 + ADX<30: N=12 W=9 L=3 PIPS=+174.2
```

The March 7/7 no-extreme subset remains high overfit risk and is not production proof.

## June-July temporal cross-check

```text
PUBLISHED=13
MATCHED=9
UNMATCHED=4
MATCH_RATE=69.2%
MATCHED_BASELINE: N=9 W=2 L=7 PIPS=-70.2
SCORE>=70 + ADX<30: N=5 W=2 L=3 PIPS=+13.1
SCORE>=70 + ADX<30 + NO_EXTREME: N=4 W=2 L=2 PIPS=+28.9
ADX_30_39: N=3 W=0 L=3 PIPS=-57.4
ADX_40_PLUS: N=1 W=0 L=1 PIPS=-25.9
```

The later matched subset supports the same ADX concern as March, but 9/13 coverage is insufficient for production approval.

## Local retention gap — verified 2026-08-07 18:58 UTC

A wider local search was run for the four unmatched June 23-26 published outcomes:

```text
TARGETS_TOTAL=4
TARGETS_WITH_NEARBY_ROWS=1
TARGETS_WITH_RELAXED_MATCH=0
TARGETS_WITH_RELAXED_COMPONENT_MATCH=0
VERDICT=LOCAL_RETENTION_GAP_CONFIRMED
```

Three targets had no same-pair/same-direction M15 rows within +/-2 days. The only target with nearby rows had no plausible identity match. The missing component rows therefore cannot be recovered from the current retained `alerts.csv`.

This closes the local-reconstruction branch of the investigation. The 9/13 June-July result remains directional evidence only.

## Supabase timestamp semantics caution

`public.signals.created_at` is publication/storage timing unless proven otherwise. It does not reliably equal watcher decision time and must not be used as the sole join key.

## Scope lock

Do not lower score/H1/Telegram thresholds, remove cooldown, add a third pair, or mutate ADX/RSI scoring yet.

Do not use `tools/backtest_bota.py` as production-rule validation because its strategy/scoring path differs from the live watcher.

## Evidence

- `audits/LOCAL_RETENTION_GAP_2026-08-07.md`
- `audits/JUNE_JULY_ADX_RSI_TEMPORAL_CROSSCHECK_2026-08-07.md`
- `audits/ADX_RSI_COUNTERFACTUAL_2026-08-07.md`
- `audits/MARCH_COMPONENT_OUTCOMES_2026-08-07.md`
- `audits/LOCAL_SIGNAL_LEDGER_INVENTORY_2026-08-07.md`
- `audits/COOLDOWN_AND_SIGNAL_QUALITY_2026-08-07.md`
- `audits/SIGNAL_DELIVERY_FUNNEL_2026-08-07.md`
- `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`
- `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
- `AI_START_HERE.md`
- `CHAT_HANDOFF_BOTA.md`
- `audits/ERROR_LOG.md`
- `ERRORS.md`

## Exactly one next action

Run a true historical replay from raw candles through the live production scoring/fusion semantics with frozen candidates:

```text
A: current baseline
B: score >=70 AND ADX <30
C: score >=70 AND ADX <30 AND no extreme RSI
```

Compare retained signal count, win/loss, total pips, and preferably MAE/MFE. No production strategy mutation until this validation is complete.
