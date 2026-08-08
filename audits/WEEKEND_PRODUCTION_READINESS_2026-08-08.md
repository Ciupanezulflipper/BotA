# BotA Weekend Production Readiness

Recorded date: **2026-08-08 UTC**

## Objective

Ship a controlled production candidate for Monday readiness without reopening closed historical-data acquisition or manufacturing signal frequency.

Target live scope:

```text
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAME=M15
```

Readiness means all three pairs are refreshed and evaluated every scheduled cycle, the existing M15/H1/H4/D1 strategy gates remain active, final actionable signals satisfy the frozen Policy-B quality guard, USDJPY risk levels use the correct JPY pip size, and Telegram/cooldown thresholds are not loosened.

It does **not** mean forcing a fixed number of Telegram signals when market conditions do not qualify.

## Evidence basis

The immutable June-July replay remains preserved at its original production source commit. The frozen candidate policies selected before the replay result were:

```text
A = current production acceptance
B = A AND score >=70 AND ADX <30
C = B AND no extreme RSI
```

Observed uniquely reconstructed published outcomes were:

```text
A: N=9 W=3 L=6 C=0 PIPS=-23.50
B: N=5 W=3 L=2 C=0 PIPS=+54.50
C: N=5 W=3 L=2 C=0 PIPS=+54.50
```

Policy C added no incremental benefit over B in that sample. This change therefore promotes **B only** as a controlled production quality guard; it does not add the RSI exclusion.

## Production implementation

### Final policy boundary

`tools/production_signal_policy.py` runs after the existing M15/H1/H4/D1 fusion decision. Existing rejected/HOLD rows are preserved. A currently accepted M15 BUY/SELL is actionable only when:

```text
score >= POLICY_B_SCORE_MIN      # production value 70
ADX   <  POLICY_B_ADX_MAX        # production value 30
```

ADX is read from an explicit top-level field when present and otherwise from the audited `adx=...` value in scoring reasons. Missing/non-finite ADX fails closed for an otherwise accepted M15 trade.

The existing H1-opposite `ADX>=40` override defect is not repaired in this production candidate because Policy B rejects `ADX>=30` after current fusion. Therefore the dead high-ADX override cannot change the accepted Policy-B set. It remains a cleanup item, not a Monday-readiness blocker.

### USDJPY risk correctness

The legacy scoring engine caps distances using `0.0001` for all pairs. That is correct for EURUSD/GBPUSD but incorrect for JPY pairs. The final production policy rewrites USDJPY M15 SL/TP from the signal entry and ATR using:

```text
JPY_PIP=0.01
SL_DISTANCE=min(ATR * SCALP_SL_ATR_MULT, MAX_SL_PIPS * 0.01)
TP_DISTANCE=min(ATR * SCALP_TP_ATR_MULT, MAX_TP_PIPS * 0.01)
```

Production defaults remain `2.0x ATR / 4.0x ATR`, capped at `30 / 60` pips. EURUSD/GBPUSD risk levels are not rewritten.

### D1 trend cache

`tools/sync_d1_trend_cache.py` derives `d1_trend_<PAIR>.json` from the already-built local D1 indicator bundles for EURUSD, GBPUSD and USDJPY. This avoids extra provider calls and keeps the D1 trend cache on the same local candle state as the indicator pipeline.

### Canonical scheduler

`ops/bota_crontab.canonical` explicitly sets:

```text
PAIRS="EURUSD GBPUSD USDJPY"
POLICY_B_ENABLED=1
POLICY_B_SCORE_MIN=70
POLICY_B_ADX_MAX=30
NEWS_ON=0
```

The updater already fetches M15/H1/H4/D1 for all three pairs. After a successful updater cycle the D1 trend-cache sync runs locally.

`NEWS_ON=0` freezes the unvalidated RSS score adjustment out of this production candidate so the score used by Policy B is the same deterministic strategy score used by the evidence base.

## Historical replay integrity

The canonical June-July replay is **not rerun or rewritten**. Its source proof belongs to historical production commit:

```text
6b437179cc58021aa358b1d0b04c121d9304c660
```

The deterministic replay test now verifies the frozen production blob map against that historical commit. Current production is allowed to evolve without weakening or silently relabeling the old replay evidence.

## Explicit non-changes

```text
NO_HISTORICAL_DATA_REACQUISITION=YES
NO_REPLAY_RESULT_REWRITE=YES
NO_RSI_POLICY_C=YES
NO_H1_THRESHOLD_LOOSENING=YES
NO_TELEGRAM_THRESHOLD_LOOSENING=YES
NO_COOLDOWN_REMOVAL=YES
NO_SUPABASE_SCHEMA_CHANGE=YES
NO_FORCED_SIGNAL_COUNT=YES
```

## Acceptance gate before deployment

The production candidate must have:

```text
focused offline tests PASS
bash syntax PASS
Security Scan PASS
DeepSource Python/Shell/Secrets PASS
Sonar quality gate PASS with 0 new issues and 0 hotspots
review findings resolved or explicitly superseded
branch behind main = 0
```

Only after merge is one bounded Termux deployment/verification package allowed.
