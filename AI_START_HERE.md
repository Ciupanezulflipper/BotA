# BotA AI Start Here

Last updated: 2026-08-07 17:38 UTC

Read this before proposing BotA commands, code, cron, service, strategy,
notification, provider, Supabase, or deployment changes.

## Current authoritative truth

```text
RECORDED_DATE=2026-08-07
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=73b2306b5843f3396823ce815e96051abf78cf50
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_CONTROL_PLANE=DEGRADED_6_OWNED_1_ORPHAN
CURRENT_REQUIRED_RUNNING=7_OF_7
CURRENT_ORPHAN_SERVICE=crond
CURRENT_DUPLICATE_SERVICE_ROWS=0
LIVE_WATCHER=RUNNING
LIVE_PAIRS=EURUSD_GBPUSD_ONLY
LIVE_TIMEFRAME=M15
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
VALID_ENTRY_ROWS=1495
BUY_SELL_VALID_ROWS=1427
BUY_SELL_ACCEPTED=110
BUY_SELL_REJECTED=1317
REJECTED_SCORE_GATE=903
REJECTED_H1_NEUTRAL=410
REJECTED_H4_D1_OPPOSE=4
ACCEPTED_LOG_EVENTS_PARSED=106
TELEGRAM_SENT=61
TELEGRAM_COOLDOWN=38
TELEGRAM_SCORE_GATE=6
TELEGRAM_FAILED=1
ACCEPTED_WITHOUT_MATCHED_RETAINED_LOG=4
ZERO_ENTRY_ROOT_CAUSE=NO
STRATEGY_MUTATION_ALLOWED=NO_PENDING_OUTCOME_PROOF
```

## Evidence order

1. `audits/SIGNAL_DELIVERY_FUNNEL_2026-08-07.md`
2. `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`
3. `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
4. `CONTINUITY_CURRENT.md`
5. `CHAT_HANDOFF_BOTA.md`
6. `audits/ERROR_LOG.md`
7. `ERRORS.md`
8. dated runtime/deployment records from 2026-08-01 through 2026-08-07

## Current signal answer — 2026-08-07

The bot is not failing because it cannot generate BUY/SELL decisions. The historical valid-tradeable funnel is measured directly:

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 524 survive M15 score gate
  -> 410 rejected by H1-neutral veto
  -> 114 survive H1
  -> 4 rejected by H4+D1 opposition
  -> 110 strategy-accepted
```

The dominant strategy bottlenecks are therefore:

```text
M15 score gate = 903 rejects = 68.56% of rejected valid BUY/SELL
H1 neutral     = 410 rejects = 31.13%
H4+D1 oppose   = 4 rejects   = 0.30%
```

`macro6=3` is neutral in current fusion code and is not the hard reject. RR text is advisory in current `quality_filter.py`. Zero entry/SL/TP occurs only on HOLD rows in the audited corpus and is not the current BUY/SELL root cause.

## Current live configuration — 2026-08-07 17:38 UTC

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

Important: the live watcher currently scans only EURUSD and GBPUSD. It cannot produce a live third-pair signal unless `PAIRS` is intentionally changed later.

The current policy is layered:

```text
strategy score floor = 65
H1-neutral override score = 75
Telegram score floor = 70
Telegram yellow floor = 70
Telegram green floor = 75
cooldown = 30 minutes per pair/timeframe
```

Therefore a strategy-accepted H1-confirmed score 65.00-69.99 signal can still be suppressed by Telegram.

## Accepted -> Telegram proof

Retained `logs/cron.signals.log` produced 106 matched strategy-accepted events:

```text
telegram_sent=61
telegram_cooldown=38
telegram_score_gate=6
telegram_failed=1
telegram_tier_gate=0
delivery_dedup=0
dry_run_or_disabled=0
telegram_backoff=0
accepted_no_terminal_evidence=0
```

Percent of the 106 parsed accepted events:

```text
sent=57.55%
cooldown=35.85%
Telegram score gate=5.66%
send failure=0.94%
```

The CSV has 110 accepted BUY/SELL rows, so four accepted rows do not have matched retained watcher-log evidence in this audit and must remain delivery-unknown.

Telegram transport itself is not the dominant defect: 61 retained accepted events were sent successfully and only one transport failure was observed.

## CSV observability defect

The live `logs/alerts.csv` has a 13-column legacy header while newer rows contain 25 columns. The first 13 positions remain aligned for the current funnel audit, but newer structured readers expecting `filter_rejected`/`filter_reasons` by header name can misclassify rows. Treat this as a separate observability/schema defect.

## Current runtime/control-plane finding

Latest observed runtime topology:

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

The ownership defect remains real, but the watcher is running and recording decisions. Do not resume broad manager-provenance archaeology unless runtime safety directly requires it.

## Scope lock

Do not change the strategy score floor, H1 protection, Telegram score floor, cooldown, pair list, provider semantics, Supabase semantics, or service topology until outcome evidence identifies the least damaging change.

The first candidate repair should be the least strategy-invasive one. In particular, delivery suppression after a strategy-accepted decision should be tested before weakening protective strategy gates.

Never push directly to `main`. Use branch -> complete content -> verified diff -> PR.

## Evidence rules

- VERIFIED = direct current evidence.
- ASSUMED = plausible but unproven.
- UNKNOWN = insufficient evidence; must not drive mutation.
- Validate CSV/file schemas before field-based analysis.
- Separate runtime health, strategy rejection, Telegram eligibility, cooldown/dedup, transport, and persistence.
- Prefer small pager-proof proofs over broad repository/terminal dumps.

## Exactly one next action

Classify outcomes for already strategy-accepted candidates that were suppressed by the Telegram score gate or 30-minute cooldown. Compare those outcomes with sent signals before changing any protective strategy threshold. Separately retain the fact that only two live pairs are configured.