# BotA Forensic Operating Model

Effective: **2026-08-07**

## Why this exists

BotA investigation became too manual and serial. Repeated one-off Termux/Python probes were useful for discovery, but they caused repeated parsing mistakes, duplicated work, and slow handoffs even though substantial history already existed across GitHub, local logs, local CSVs, and Supabase.

This document defines the default workflow going forward.

## 1. Evidence-source hierarchy

Use the cheapest authoritative source first.

```text
GitHub connector
  -> code, commit/PR history, docs, tests, implementation semantics

Supabase connector
  -> published signal rows, lifecycle/outcome truth, database state

Phone/Termux
  -> /proc runtime state, local .env values, local-only logs/caches, provider credentials
```

Do not ask the phone to rediscover information already available through GitHub or Supabase.

## 2. Replace one-off probes with one reusable snapshot tool

Target capability: `tools/bota_forensics.py` (or equivalent).

One read-only command should emit a small machine-readable JSON report plus a concise human summary containing at least:

- recorded UTC timestamp and repo/runtime identifiers;
- live pairs/timeframes and effective thresholds;
- service/watcher state;
- alerts schema/column-count drift;
- raw -> rejected -> accepted funnel counts;
- accepted -> Telegram outcome counts;
- local ledger coverage/outcomes;
- raw candle coverage by pair/timeframe;
- checksums and explicit data-retention gaps.

The tool must be deterministic, bounded, read-only, secret-safe, and versioned in GitHub. New investigations should extend this tool/tests instead of creating another large shell here-document whenever practical.

## 3. Build one immutable replay dataset

Target capability: a historical-data acquisition tool that writes only under a replay/research namespace, never production cache paths.

Recommended contract:

```text
data/replay/<dataset_id>/
  manifest.json
  EURUSD/M15.csv
  EURUSD/H1.csv
  EURUSD/H4.csv
  EURUSD/D1.csv
  GBPUSD/M15.csv
  GBPUSD/H1.csv
  GBPUSD/H4.csv
  GBPUSD/D1.csv
```

The manifest must record provider, requested start/end, actual first/last timestamps, row counts, timeframe checks, hashes, acquisition time, and gaps/duplicates. Historical fetches must support explicit date ranges/pagination. They must never overwrite `cache/*` or `data/candles/*`.

## 4. One deterministic production-path replay

Do not validate production strategy changes with `tools/backtest_bota.py` while its semantics differ from the live watcher.

Target capability: replay the live indicator/scoring/fusion semantics against historical candle prefixes with an explicit evaluation timestamp. Current-time, current-cache, Telegram, provider, and publication side effects must be disabled or injected deterministically.

Freeze candidate policies before validation:

```text
A = current production baseline
B = score >= 70 AND ADX < 30
C = score >= 70 AND ADX < 30 AND no extreme RSI
```

March is discovery evidence. Later data is validation evidence. Do not repeatedly tune a rule on the same holdout until it looks good.

## 5. Decision gate before production mutation

Default sequence:

```text
OBSERVATION
  -> REPRODUCIBLE EVIDENCE
  -> OFFLINE REPLAY
  -> TEMPORAL/HOLDOUT VALIDATION
  -> CODE PR + TESTS
  -> SHADOW OBSERVATION
  -> PRODUCTION
```

A drought of Telegram messages is not by itself justification to lower thresholds. A tiny winning subset is not sufficient production proof.

## 6. Documentation discipline

Avoid updating many overlapping narrative files after every small probe.

- `AI_START_HERE.md`: compact current truth and pointer to canonical state.
- `CONTINUITY_CURRENT.md`: one authoritative current state, blockers, and exactly one next engineering objective.
- `audits/YYYY...md`: dated milestone evidence when a finding is verified.
- `ERRORS.md` / `audits/ERROR_LOG.md`: only confirmed reusable failure classes/process incidents.
- `CHAT_HANDOFF_BOTA.md`: update when the handoff materially changes, not after every counter.

All runtime evidence must include its actual device UTC recording time.

## 7. Conversation/command discipline

Each investigation step should have exactly four visible parts:

```text
FINDING
DECISION
ONE ACTION
PASS/FAIL CONDITION
```

Prefer connector work that does not require user interaction. When Termux is necessary, provide one bounded command with capped output. Do not send another long ad-hoc probe if the same fact can be obtained by extending the reusable forensic tool.

## Current implementation priority

As of 2026-08-07, the immediate blocker is not another strategy hypothesis. It is missing replayable M15/H1 history for June–July.

Engineering order:

```text
1. reusable forensic snapshot tool
2. immutable historical data collector + integrity manifest
3. deterministic live-path replay harness
4. replay frozen A/B/C policies
5. only then consider scoring/filter mutation
```
