# BotA AI Start Here

Last updated: 2026-08-07 17:11 UTC

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
VALID_ENTRY_ROWS=1495
BUY_SELL_VALID_ROWS=1427
BUY_SELL_ACCEPTED=110
BUY_SELL_REJECTED=1317
BUY_SELL_ACCEPTANCE_RATE=7.71_PERCENT
BUY_SELL_REJECTION_RATE=92.29_PERCENT
REJECTED_SCORE_GATE=903
REJECTED_H1_NEUTRAL=410
REJECTED_H4_D1_OPPOSE=4
ZERO_ENTRY_ROOT_CAUSE=NO
TELEGRAM_DELIVERY_OF_ACCEPTED=NOT_YET_PROVEN
STRATEGY_MUTATION_ALLOWED=NO_PENDING_CURRENT_THRESHOLD_AND_DELIVERY_PROOF
```

## Evidence order

1. `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`
2. `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
3. `CONTINUITY_CURRENT.md`
4. `CHAT_HANDOFF_BOTA.md`
5. `audits/ERROR_LOG.md`
6. `ERRORS.md`
7. dated runtime/deployment records from 2026-08-01 through 2026-08-07

## Current signal answer — 2026-08-07

The live direction engine is not dead. The valid tradeable historical funnel is now measured directly:

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 524 survive M15 score gate
  -> 410 rejected by H1-neutral veto
  -> 114 survive H1
  -> 4 rejected by H4+D1 opposition
  -> 110 accepted
```

Rejected-stage percentages:

```text
score gate=68.56%
H1 neutral=31.13%
H4+D1 opposition=0.30%
```

This is the strongest current explanation for low strategy throughput. The system does create BUY/SELL directions, but only 7.71% of valid BUY/SELL rows survive the strategy/filter gates in the inspected corpus.

## Important interpretations

- `macro6=3` appears in every accepted and rejected valid BUY/SELL row in this corpus. Current fusion code treats it as neutral and applies zero score adjustment. It is not the hard rejection cause.
- RR strings are advisory in current `quality_filter.py`; they co-occur with hard score/H1 gates and are not the primary cause here.
- `H4_D1_oppose` rejected only four valid BUY/SELL rows and is not a dominant bottleneck.
- The historical corpus spans different score thresholds (`score<62`, `score<65`, `score<70`). Do not infer the current threshold from aggregate history.
- All zero-entry/SL/TP rows were HOLD score-0 rows. No BUY/SELL row had zero entry. Zero entry is not the current root cause.

## CSV observability defect

The live `logs/alerts.csv` has a 13-column legacy header while 2509 observed data rows contain 25 columns. The first 13 positions remain semantically aligned, so current funnel counts based on direction, score, entry/SL/TP, `rejected`, and `filter_str` are usable.

However, newer structured readers that expect `filter_rejected` and `filter_reasons` column names may misclassify historical rows. Treat this as a separate observability/schema defect, not a strategy explanation.

## Telegram remains a separate acceptance gate

The 110 accepted rows are not proof that 110 user-visible signals were sent. Current watcher code still applies:

```text
TELEGRAM_MIN_SCORE
TELEGRAM_TIER_YELLOW_MIN
TELEGRAM_COOLDOWN_SECONDS
delivery dedup
Telegram transport
```

Before any threshold change, prove the current effective phone values and retained accepted -> Telegram outcomes.

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

The ownership defect remains real, but the watcher is running and writing decisions. Do not use this defect as the default explanation for low signal throughput.

## Scope lock

Do not change score thresholds, H1/H4/D1 behavior, macro policy, RR, SL/TP, provider semantics, Telegram eligibility, dedup, Supabase semantics, or service topology until current threshold and delivery evidence is captured.

Do not resume broad manager-provenance archaeology unless runtime safety directly requires it.

Never push directly to `main`. Use branch -> complete content -> verified diff -> PR.

## Evidence rules

- VERIFIED = direct current evidence.
- ASSUMED = plausible but unproven.
- UNKNOWN = insufficient evidence; must not drive mutation.
- Validate CSV/file schemas before field-based analysis.
- Separate runtime health, strategy rejection, Telegram eligibility, cooldown/dedup, transport, and persistence.
- Prefer small pager-proof proofs over broad repository/terminal dumps.

## Exactly one next action

Read only the current phone values for score/H1/Telegram thresholds and classify retained watcher-log outcomes after strategy acceptance: score gate, tier gate, cooldown, dedup, send success, or send failure. No mutation before that proof.
