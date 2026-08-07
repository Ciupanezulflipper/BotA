# BotA Current Continuity State

Last updated: **2026-08-07 19:10 UTC**

## Authoritative identifiers

```text
RECORDED_DATE=2026-08-07
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=73b2306b5843f3396823ce815e96051abf78cf50
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_SERVICE_DAEMON_PIDFILE=31140
```

## Runtime and live scope

```text
manager_count=1
required_services_running=7/7
owned_services=6/7
orphan_service=crond
watcher=RUNNING
PAIRS=EURUSD GBPUSD
TIMEFRAMES=M15
FILTER_SCORE_MIN_ALL=65
H1_VETO_OVERRIDE_SCORE=75
TELEGRAM_MIN_SCORE=70
TELEGRAM_TIER_YELLOW_MIN=70
TELEGRAM_TIER_GREEN_MIN=75
TELEGRAM_COOLDOWN_SECONDS=1800
DRY_RUN_MODE=0
TELEGRAM_ENABLED=1
```

Runtime ownership remains degraded, but the watcher is producing decisions and Telegram transport is proven to work. Only two pairs are live.

## Proven signal funnel

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 410 rejected by H1-neutral veto
  -> 4 rejected by H4+D1 opposition
  -> 110 strategy-accepted
```

Retained accepted-to-Telegram outcomes:

```text
61 sent
38 cooldown-suppressed
6 Telegram score-gated
1 send failure
```

The current dominant strategy-quality question is not whether BotA can emit signals; it can. The problem is that recent high-confidence published signals have poor realized outcomes.

## Outcome evidence

Supabase BotA M15 published outcomes on/after 2026-06-01:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
```

March local ledger joined 51/51 to score components:

```text
BASELINE: N=51 W=13 L=38 PIPS=-264.1
ADX<30: N=17 W=9 L=8 PIPS=+98.0
SCORE>=70 + ADX<30: N=12 W=9 L=3 PIPS=+174.2
```

Later June–July component cross-check recovered 9/13 published signals:

```text
MATCHED_BASELINE: N=9 W=2 L=7 PIPS=-70.2
SCORE>=70 + ADX<30: N=5 W=2 L=3 PIPS=+13.1
SCORE>=70 + ADX<30 + NO_EXTREME: N=4 W=2 L=2 PIPS=+28.9
ADX>=30 within matched sample: 0W / 4L / -83.3 pips
```

This is cross-period evidence that ADX calibration deserves replay testing, but it is not production approval.

## Local signal-row retention gap

Verified 2026-08-07 18:58 UTC:

```text
UNMATCHED_PUBLISHED_TARGETS=4
RELAXED_LOCAL_MATCHES=0
RELAXED_COMPONENT_MATCHES=0
LOCAL_RETENTION_GAP=CONFIRMED
```

Stop trying to reconstruct those four rows from `logs/alerts.csv`.

## Raw candle replay prerequisite — verified 2026-08-07 19:10:26 UTC

The canonical candle CSVs are valid ISO-timestamp CSV files. A prior numeric-only inventory parser incorrectly reported zero rows; that result is superseded.

Verified retained input coverage for both EURUSD and GBPUSD:

```text
M15: 499 rows, 2026-07-31 15:00 UTC -> 2026-08-07 19:30 UTC
H1 : 499 rows, 2026-07-10 00:00 UTC -> 2026-08-07 18:00 UTC
H4 : 499 rows, 2026-04-14 13:00 UTC -> 2026-08-07 13:00 UTC
D1 : 499 rows, 2024-09-02 21:00 UTC -> 2026-08-05 21:00 UTC
```

Standalone `data/EURUSD_M15.csv` and `data/GBPUSD_M15.csv` contain 500 rows only from 2026-02-27 through 2026-03-06. They do **not** cover June–July.

Therefore:

```text
M15_JUNE_JULY_INPUT_COVERAGE=NO
H1_JUNE_JULY_INPUT_COVERAGE=NO
H4_JUNE_JULY_INPUT_COVERAGE=YES
D1_JUNE_JULY_INPUT_COVERAGE=YES
TRUE_REPLAY_FROM_RETAINED_INPUTS=BLOCKED
```

Current `tools/data_fetch_candles.sh` is a rolling live fetcher (`count=500`) and must not be used as the replay data collector because it does not provide the required historical range and writes live cache paths.

## Efficiency operating model

Canonical workflow: `docs/FORENSIC_OPERATING_MODEL.md`.

Going forward:

```text
GitHub connector -> code/history/docs/tests
Supabase connector -> published signal/outcome truth
Phone/Termux -> runtime-only and local-private evidence
```

Replace repeated one-off shell/Python probes with a versioned reusable forensic snapshot tool. Build an immutable historical dataset under a replay namespace, then a deterministic replay of the live production semantics. Do not repeatedly rediscover facts already available through connectors.

## Scope lock

Do not lower score/H1/Telegram floors, remove cooldown, add a third pair, or mutate ADX/RSI scoring yet.

Do not use `tools/backtest_bota.py` as production-rule validation because its strategy/scoring path differs from the live watcher.

Never push directly to `main`; use branch -> complete-file writes -> diff -> PR.

## Evidence

- `audits/RAW_CANDLE_REPLAY_GAP_2026-08-07.md`
- `docs/FORENSIC_OPERATING_MODEL.md`
- `audits/LOCAL_RETENTION_GAP_2026-08-07.md`
- `audits/JUNE_JULY_ADX_RSI_TEMPORAL_CROSSCHECK_2026-08-07.md`
- `audits/ADX_RSI_COUNTERFACTUAL_2026-08-07.md`
- `audits/MARCH_COMPONENT_OUTCOMES_2026-08-07.md`
- `audits/LOCAL_SIGNAL_LEDGER_INVENTORY_2026-08-07.md`
- `audits/COOLDOWN_AND_SIGNAL_QUALITY_2026-08-07.md`
- `audits/SIGNAL_DELIVERY_FUNNEL_2026-08-07.md`
- `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`
- `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`

## Exactly one next engineering objective

Implement the reusable **replay infrastructure**, beginning with an immutable paginated historical-data collector and integrity manifest for the missing M15/H1 June–July inputs. This is engineering work, not another manual forensic probe.

After the dataset is verified, run the frozen policies through a deterministic live-path replay:

```text
A = current production baseline
B = score >=70 AND ADX <30
C = score >=70 AND ADX <30 AND no extreme RSI
```

No production strategy mutation before that replay.
