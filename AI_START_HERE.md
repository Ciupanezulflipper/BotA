# BotA AI Start Here

Last updated: **2026-08-07 23:46 UTC**

Read this before proposing BotA commands, code, service, strategy, Telegram, provider, Supabase, replay, or deployment changes.

## Current authoritative truth

```text
RECORDED_DATE=2026-08-07
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=73b2306b5843f3396823ce815e96051abf78cf50
GITHUB_MAIN_AT_PHASE2_RUNNER_MERGE=91f81ddf28e6b0fadfa2e87a3f71f9464c962073
LIVE_WATCHER=RUNNING
LIVE_PAIRS=EURUSD_GBPUSD_ONLY
LIVE_TIMEFRAME=M15
FILTER_SCORE_MIN_ALL=65
H1_VETO_OVERRIDE_SCORE=75
TELEGRAM_MIN_SCORE=70
TELEGRAM_COOLDOWN_SECONDS=1800
DRY_RUN_MODE=0
TELEGRAM_ENABLED=1
HISTORICAL_DATA_PHASE=CLOSED_PASS
DETERMINISTIC_REPLAY_HARNESS_PHASE=CLOSED_PASS
FULL_JUNE_JULY_REPLAY_EXECUTION=CLOSED_PASS
OUTCOME_MATCH_AND_ABC_COMPARISON=NEXT
PRODUCTION_STRATEGY_MUTATION_ALLOWED=NO
```

## Read first

1. `CONTINUITY_CURRENT.md` — current state and exactly one next action.
2. `audits/DETERMINISTIC_REPLAY_PHASE2_EXECUTION_2026-08-07.md` — canonical Phase-2 execution proof.
3. `audits/DETERMINISTIC_REPLAY_PHASE1_PROOF_2026-08-07.md` — reviewed replay-harness provenance.
4. `docs/FORENSIC_OPERATING_MODEL.md` — mandatory connector-first workflow.

Older dated audits remain evidence. Do not restart closed acquisition/runtime branches without new contradictory evidence.

## Current diagnosis

BotA can emit BUY/SELL decisions and Telegram can send them. The investigation is now about **signal quality/calibration**, not basic transport, historical-data availability, or replay determinism.

Known published outcome evidence for BotA M15 on/after 2026-06-01 remains poor:

```text
SUPABASE_JUNE_JULY_TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
```

Earlier March and partial June-July component audits made ADX/RSI calibration worth testing, but did not authorize production changes.

## Canonical historical dataset

```text
DATASET_ID=oanda-warmup-20240101-20260801-20260807-r3
RAW_RANGE=[2024-01-01T00:00:00Z,2026-08-01T00:00:00Z)
EVALUATION_RANGE=[2026-06-01T00:00:00Z,2026-08-01T00:00:00Z)
REPLAY_DATASET_ELIGIBLE=YES
DATASET_MANIFEST_SHA256=e0033c797fc561935beebd27eaa275c0c659ccaac93acfaa2309abf8354ecf2f
```

Do not reacquire this interval unless r3 itself is proven corrupt. Two earlier failed immutable acquisition roots remain forensic evidence and must not be deleted/reused.

## Deterministic replay result

Reviewed replay source:

```text
PHASE1_REPLAY_MERGE=6b437179cc58021aa358b1d0b04c121d9304c660
PHASE2_RUNNER_PR=66
PHASE2_RUNNER_MERGE=91f81ddf28e6b0fadfa2e87a3f71f9464c962073
PHASE2_RUNNER_BLOB=bed536931026231956536543b914703e7ee096d2
CANONICAL_REPLAY_RESULT=data/replay_results/phase2-june-july-pr64
```

The phone executed the merged runner twice against r3. Exact proof:

```text
RUN1_RC=0
RUN2_RC=0
RUN1_EVENTS_SHA256=05089e6d97e4ab9f3a522d9ec1188c24e69637bf048f1cd1403f23772ec8dabc
RUN2_EVENTS_SHA256=05089e6d97e4ab9f3a522d9ec1188c24e69637bf048f1cd1403f23772ec8dabc
RUN1_SUMMARY_SHA256=f00e42962dd08f7aef7f5e2ecb5d3475d57bbca8abc3bce9f4d2d0d70b903594
RUN2_SUMMARY_SHA256=f00e42962dd08f7aef7f5e2ecb5d3475d57bbca8abc3bce9f4d2d0d70b903594
EVENT_BYTES_IDENTICAL=YES
SUMMARY_BYTES_IDENTICAL=YES
PRODUCTION_SOURCE_BLOBS_MATCH=YES
PRODUCTION_CACHE_UNCHANGED=YES
TRACKED_WORKTREE_UNCHANGED=YES
PHASE2_DETERMINISM_GATE=PASS
```

Replay grade:

```text
DETERMINISTIC_PRODUCTION_RULES_WITH_PROVIDER_SUBSTITUTION
```

The known provider-substitution and D1 fail-open limitations remain explicit; deterministic does not mean perfect historical identity to every unretained live network/cache input.

## Frozen A/B/C policies

These policies were fixed before observing the full June-July replay counts:

```text
A = current production acceptance
B = A AND score >=70 AND ADX <30
C = B AND no extreme RSI
SELL extreme RSI <=30
BUY  extreme RSI >=70
```

Full deterministic reconstruction produced:

```text
DECISION_ROWS=8618
POLICY_A_ACCEPTED=105
POLICY_B_ACCEPTED=51
POLICY_C_ACCEPTED=45
REJECTION_STAGES={ACCEPTED:105,H1_CONFIRM:461,H4_D1_CONFIRM:10,M15_SETUP_OR_SCORE:4104,MARKET_CLOSED:3938}
```

These are acceptance counts, **not performance results**. Do not infer that B or C is better merely because it accepts fewer events.

## Important production-code finding preserved by replay

Current `m15_h1_fusion.sh` reads top-level `.adx // 0` for the H1-opposite override, while current scoring JSON does not emit a top-level `adx` field. Therefore the intended `ADX>=40` opposite-trend override receives zero and cannot activate under the inspected production contract.

Replay reproduces this behavior. Do not fix production yet; outcome/robustness evidence comes first.

## Mandatory source hierarchy

```text
GitHub connector   -> code, commits, PRs, docs, tests
Supabase connector -> published signal/outcome/database truth
Phone/Termux       -> runtime-only state, credentials, local-only immutable data/results
```

Do not ask for ad-hoc phone probes for facts already obtainable through connectors. Reusable reviewed tools are preferred when local-only evidence must be consumed.

## Scope lock

Until outcome matching plus robustness/holdout evidence completes:

```text
DO_NOT_LOWER_SCORE_FLOOR=YES
DO_NOT_LOWER_H1_FLOOR=YES
DO_NOT_CHANGE_TELEGRAM_FLOORS=YES
DO_NOT_REMOVE_COOLDOWN=YES
DO_NOT_ADD_THIRD_PAIR=YES
DO_NOT_MUTATE_ADX_RULE=YES
DO_NOT_MUTATE_RSI_RULE=YES
DO_NOT_FIX_H1_ADX_OVERRIDE_IN_PRODUCTION_YET=YES
```

Do not use `tools/backtest_bota.py` as production-rule validation because its strategy semantics differ from the live watcher.

Never push directly to `main`. Use branch -> complete-file writes -> verified diff -> PR -> exact-head gates -> merge.

## Exactly one next action

Build and review one reusable outcome-matching tool that consumes:

```text
data/replay_results/phase2-june-july-pr64/events.jsonl
```

and a frozen Supabase June-July outcome snapshot, then computes matched outcome statistics for policies A/B/C.

Matching must not use Supabase `created_at` as a sole identity key. Require pair + direction and use bounded entry-price + temporal consistency; report ambiguity instead of forcing a match.

No production strategy mutation before this comparison and the later robustness/final-verdict phase.
