# Local Signal Ledger Inventory — 2026-08-07

Recorded: 2026-08-07 18:09:45 UTC

## Purpose

Determine whether the existing local `data/ledger.csv` can be used as a current offline outcome dataset for scoring-component analysis.

## Verified phone evidence

```text
LEDGER_EXISTS=True
LEDGER_BYTES=5631
LEDGER_ROWS=51
FIELDS=timestamp,pair,tf,direction,score,entry,sl,tp,sl_pips,tp_pips,rr_ratio,outcome,result_pips,bars_to_close,max_adverse,max_favorable
LOSS=38
WIN=13
FIRST_TIMESTAMP=2026-03-09T21:45:07+02:00
LAST_TIMESTAMP=2026-03-10T15:15:07+02:00
```

Observed win rate:

```text
13 / 51 = 25.49%
```

The ledger covers only about 17.5 hours from 2026-03-09 through 2026-03-10. It is therefore not a current June-August outcome corpus and must not be used by itself to judge the present strategy configuration.

## Interpretation

1. The ledger is real and contains closed outcomes, but it is stale and narrow.
2. Its 13 wins / 38 losses are a strong historical warning, not proof of current-strategy performance.
3. The next useful offline proof is to join these 51 ledger rows back to the 25-column `logs/alerts.csv` rows and inspect score components only if match coverage is high.
4. Any March component result must remain clearly separated from the more recent Supabase outcome evidence since 2026-06-01.
5. Do not loosen thresholds, cooldown, H1 protection, or pair scope based on this ledger alone.

## Current recent-quality evidence retained separately

Read-only Supabase evidence for BotA M15 signals created on or after 2026-06-01 remains:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
```

The local March ledger does not replace that recent evidence.

## Next action

Run one bounded local join:

```text
data/ledger.csv
        x
logs/alerts.csv
```

Report match coverage and outcome differences by score bucket, RSI extremity, MACD saturation, ADX band, H1 state, pair, and direction. No provider call and no mutation.
