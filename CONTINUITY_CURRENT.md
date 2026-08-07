# BotA Current Continuity State

Last updated: 2026-08-07 17:38 UTC

## Authoritative identifiers

```text
RECORDED_DATE=2026-08-07
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=73b2306b5843f3396823ce815e96051abf78cf50
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_SERVICE_DAEMON_PIDFILE=31140
```

## Current runtime state — 2026-08-07

Latest read-only control-plane observation:

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

The watcher is live and was observed through:

```text
runsv bota-watcher
  -> tools/run_signal_watcher_with_ledger.sh
  -> tools/signal_watcher_pro.sh --once
```

The ownership defect remains real but does not explain the current signal drought by itself because all seven required services are running and the watcher is actively recording decisions.

## Current effective live strategy/delivery settings — 2026-08-07 17:38 UTC

```text
PAIRS=EURUSD GBPUSD
TIMEFRAMES=M15
FILTER_SCORE_MIN=65
FILTER_SCORE_MIN_ALL=65
FILTER_SCORE_MIN_M15=<unset>
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

Current pair scope is therefore only EURUSD and GBPUSD. A third live pair is not currently scanned.

Current layered signal policy:

```text
M15 strategy hard score floor = 65
H1-neutral override score = 75
Telegram hard score floor = 70
Telegram yellow floor = 70
Telegram green floor = 75
Telegram cooldown = 1800 seconds = 30 minutes per pair/timeframe
```

This means a strategy-accepted H1-confirmed signal with score 65.00-69.99 can still be prevented from reaching Telegram.

## Signal funnel — verified 2026-08-07

Source: `logs/alerts.csv`.

Observed file shape:

```text
HEADER_COLUMNS=13
ROWS_WITH_25_COLUMNS=2509
```

Legacy header:

```text
timestamp,pair,tf,direction,score,confidence,entry,sl,tp,provider,rejected,filter_str,reasons
```

The newer watcher appends 25-column rows under this old header. The first 13 positions remain aligned for the current funnel audit, but the schema drift is an observability defect for newer named-field readers.

### Valid tradeable funnel

```text
VALID_ENTRY_ROWS=1495
BUY_SELL_VALID_ROWS=1427
BUY_SELL_ACCEPTED=110
BUY_SELL_REJECTED=1317
BUY_SELL_ACCEPTANCE_RATE=7.71%
BUY_SELL_REJECTION_RATE=92.29%
```

Direction split:

```text
BUY_ACCEPTED=61
BUY_REJECTED=407
SELL_ACCEPTED=49
SELL_REJECTED=910
```

Accepted by pair across the historical corpus:

```text
EURUSD=56
GBPUSD=53
USDJPY=1
```

The historical USDJPY row does not mean USDJPY is currently live; the present `PAIRS` setting is only EURUSD GBPUSD.

### Exact rejected-stage decomposition

```text
SCORE_GATE=903
H1_NEUTRAL=410
H4_D1_OPPOSE=4
TOTAL=1317
```

Percent of rejected valid BUY/SELL rows:

```text
SCORE_GATE=68.56%
H1_NEUTRAL=31.13%
H4_D1_OPPOSE=0.30%
```

Current source flow makes this sequential:

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 524 survive M15 score gate
  -> 410 rejected by H1-neutral veto
  -> 114 survive H1
  -> 4 rejected by H4+D1 opposition
  -> 110 strategy-accepted
```

This is the strongest direct explanation of low strategy throughput.

## Accepted -> Telegram funnel — verified 2026-08-07

Source: retained `logs/cron.signals.log`.

```text
LOG_LINES=27332
ACCEPTED_EVENTS_PARSED=106
telegram_score_gate=6
telegram_tier_gate=0
telegram_cooldown=38
delivery_dedup=0
dry_run_or_disabled=0
telegram_sent=61
telegram_backoff=0
telegram_failed=1
accepted_no_terminal_evidence=0
```

The 106 parsed accepted events classify completely:

```text
sent=61              57.55%
cooldown=38          35.85%
Telegram score gate=6 5.66%
send failure=1        0.94%
```

The CSV contains 110 accepted BUY/SELL rows, so four accepted CSV rows do not have matched retained watcher-log evidence in this audit. Keep those four as delivery-unknown.

Telegram transport itself is functioning: 61 retained accepted events were sent and only one transport failure was observed. The larger post-acceptance suppressors are the 30-minute cooldown and the separate Telegram score floor.

## Macro, RR, and zero-entry interpretation

- `macro6=3` appears in accepted and rejected rows and is neutral in current fusion logic; it is not the hard reject.
- RR text is advisory in current `quality_filter.py`; it is not the dominant hard gate.
- All zero-entry/SL/TP rows in the audited corpus were HOLD score-0 rows; no BUY/SELL row had zero entry. Zero entry is not the current root cause.

## Score history warning

Historical rows include `score<62`, `score<65`, and `score<70`, proving prior configuration changes. Do not use aggregate historical strings to infer current values. Current effective phone values are now directly recorded above.

## Practical current interpretation

The signal drought is not a single mysterious runtime failure. It is the cumulative effect of layered gates:

1. M15 score floor removes the majority of valid BUY/SELL candidates.
2. H1-neutral veto removes most remaining candidates that do not reach override conditions.
3. H4+D1 opposition removes very few.
4. After strategy acceptance, Telegram applies another score floor at 70.
5. A 30-minute per-pair/timeframe cooldown suppresses many retained accepted events.
6. Only two live pairs are configured.

No one of these facts alone proves which setting should be loosened. Protective strategy gates must be judged against candidate outcomes before mutation.

## Scope lock

No strategy score, H1/H4/D1, pair list, Telegram score, cooldown, provider, Supabase, dedup, or service-topology mutation is authorized yet.

The first potential repair should be the least strategy-invasive one and must be supported by outcome evidence for candidates already accepted by the strategy but suppressed by delivery policy.

## Evidence

- `audits/SIGNAL_DELIVERY_FUNNEL_2026-08-07.md`
- `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`
- `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
- `AI_START_HERE.md`
- `CHAT_HANDOFF_BOTA.md`
- `audits/ERROR_LOG.md`
- `ERRORS.md`

## Exactly one next action

Classify historical outcomes for strategy-accepted candidates suppressed by Telegram score or 30-minute cooldown. Compare them with delivered-signal outcomes before changing protective strategy thresholds. Separately remember that adding a third pair would require an explicit live `PAIRS` change later.