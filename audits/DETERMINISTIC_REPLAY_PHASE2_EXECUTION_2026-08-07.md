# BotA Deterministic Replay — Phase 2 Execution Proof

Recorded date: **2026-08-07**

## Scope

This audit records the first canonical full June-July deterministic execution of the reviewed BotA replay harness against the immutable r3 OANDA dataset.

This is an evidence record only. It does **not** approve any production strategy, threshold, pair, cooldown, Telegram, service, cron, Supabase, or runtime mutation.

## Canonical identifiers

```text
DATASET_ID=oanda-warmup-20240101-20260801-20260807-r3
REPLAY_SOURCE_COMMIT=6b437179cc58021aa358b1d0b04c121d9304c660
PHASE2_RUNNER_PR=66
PHASE2_RUNNER_MERGE=91f81ddf28e6b0fadfa2e87a3f71f9464c962073
PHASE2_RUNNER_BLOB=bed536931026231956536543b914703e7ee096d2
CANONICAL_REPLAY_RESULT=data/replay_results/phase2-june-july-pr64
EVALUATION_RANGE=[2026-06-01T00:00:00Z,2026-08-01T00:00:00Z)
DEVICE_UTC=2026-08-07 23:46:14 UTC
```

The outer phone launcher downloaded the merged PR #66 runner and independently proved:

```text
RUNNER_EXPECTED_BLOB=bed536931026231956536543b914703e7ee096d2
RUNNER_ACTUAL_BLOB=bed536931026231956536543b914703e7ee096d2
RUNNER_INTEGRITY=PASS
```

## Replay dependency provenance

Before execution, the merged runner downloaded the exact reviewed Phase-1 replay/source files from immutable commit `6b437179cc58021aa358b1d0b04c121d9304c660` and compared every downloaded file to its expected Git blob ID.

```text
deterministic_replay.py 498dbb9affb44f9b71e1b25bbd6228a20415914d
replay_semantics.py     6c18ddcfa7a49c5e5cb9cf139d341783dcb04a23
verify_replay_dataset.py 04dff84cbbd1a86a5508282f09b12726744778eb
build_indicators.py     2abce4a325d6d9da8bb0958b97a651d4288e1792
quality_filter.py       18b76f908652d483c115c930373972836cea81dc
sr_score.py             616b996a8ce439a19483762645a2247ca96fd066
scoring_engine.sh       09c42362a5c3c679696e86d4131ce5dfabd86608
m15_h1_fusion.sh        c1de0312ed928f870b9a45df109b730d30888ee7
market_open.sh          a73ca97f3a63c3245311585e231e5e69eaffc506
emit_snapshot.py        425c9adace57956981cf7e3111fd5df504c4f1ca
```

Final source gate:

```text
REPLAY_SOURCE_INTEGRITY=PASS
PRODUCTION_SOURCE_BLOBS_MATCH=YES
```

## Double-run determinism proof

Both full replay executions completed successfully:

```text
RUN1_RC=0
RUN2_RC=0
```

Event ledgers were byte-identical:

```text
RUN1_EVENTS_SHA256=05089e6d97e4ab9f3a522d9ec1188c24e69637bf048f1cd1403f23772ec8dabc
RUN2_EVENTS_SHA256=05089e6d97e4ab9f3a522d9ec1188c24e69637bf048f1cd1403f23772ec8dabc
EVENT_BYTES_IDENTICAL=YES
```

Summary files were byte-identical:

```text
RUN1_SUMMARY_SHA256=f00e42962dd08f7aef7f5e2ecb5d3475d57bbca8abc3bce9f4d2d0d70b903594
RUN2_SUMMARY_SHA256=f00e42962dd08f7aef7f5e2ecb5d3475d57bbca8abc3bce9f4d2d0d70b903594
SUMMARY_BYTES_IDENTICAL=YES
```

The replay recorded the exact immutable dataset manifest hash:

```text
DATASET_MANIFEST_SHA256=e0033c797fc561935beebd27eaa275c0c659ccaac93acfaa2309abf8354ecf2f
```

## Replay grade and funnel

```text
REPLAY_STATUS=COMPLETE
REPLAY_GRADE=DETERMINISTIC_PRODUCTION_RULES_WITH_PROVIDER_SUBSTITUTION
DECISION_ROWS=8618
```

Frozen-policy counts:

```text
POLICY_A_ACCEPTED=105
POLICY_B_ACCEPTED=51
POLICY_C_ACCEPTED=45
```

Where the policies were frozen before full replay as:

```text
A = current production acceptance
B = A AND score >=70 AND ADX <30
C = B AND no extreme RSI
SELL extreme RSI <=30
BUY  extreme RSI >=70
```

Replay rejection funnel:

```text
ACCEPTED=105
H1_CONFIRM=461
H4_D1_CONFIRM=10
M15_SETUP_OR_SCORE=4104
MARKET_CLOSED=3938
TOTAL=8618
```

The counts above are **decision reconstruction counts**, not trade-performance results. No inference about profit, loss, win rate, or production approval may be made from acceptance counts alone.

## Production isolation proof

The production candle cache hash was identical before and after both replays:

```text
PRODUCTION_CACHE_SHA256_BEFORE=8d407d175e23929dd3ff2c898ee994670ca1057a2dfdfd0c3c61acc91fbb0847
PRODUCTION_CACHE_SHA256_AFTER=8d407d175e23929dd3ff2c898ee994670ca1057a2dfdfd0c3c61acc91fbb0847
PRODUCTION_CACHE_UNCHANGED=YES
```

Tracked worktree state was also unchanged:

```text
TRACKED_WORKTREE_UNCHANGED=YES
```

The runner explicitly reported:

```text
PRODUCTION_STRATEGY_MUTATION=NO
TELEGRAM_MUTATION=NO
SUPABASE_MUTATION=NO
SERVICE_CRON_MUTATION=NO
TEMP_REPLAY_FILES_RETAINED=NO
```

The canonical result directory was published only after all determinism/provenance/isolation gates passed, using the exclusive + atomic publication behavior reviewed in PR #66.

## Phase 2 verdict

```text
PHASE2_DETERMINISM_GATE=PASS
FULL_JUNE_JULY_REPLAY_EXECUTION=PASS
DETERMINISTIC_EVENT_LEDGER=AVAILABLE_LOCAL_ONLY
PRODUCTION_STRATEGY_MUTATION_ALLOWED=NO
```

This closes the deterministic execution gate. It does **not** close strategy calibration.

## Supabase outcome truth for the frozen evaluation interval

After the replay pass, the Supabase connector was re-queried for `public.signals` in `[2026-06-01, 2026-08-01)`.

The database still contains 13 BotA M15 published outcomes in the interval:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
```

`created_at` remains non-authoritative as a sole replay join key because publication time can differ from watcher decision time.

## Exactly one next action

Build and review one reusable outcome-matching tool that consumes the canonical local replay event ledger and a frozen Supabase outcome snapshot, then:

1. requires pair + direction agreement;
2. uses entry-price and bounded temporal consistency together;
3. reports candidate ambiguity rather than forcing a join;
4. never treats `created_at` alone as identity;
5. computes observed outcome statistics for frozen policies A/B/C only after the matching gate is explicit and reproducible.

No ADX/RSI, score, H1, Telegram, cooldown, pair-scope, or production strategy mutation before that comparison and the later robustness/holdout verdict.
