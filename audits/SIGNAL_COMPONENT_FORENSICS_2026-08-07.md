# BotA Recent Delivered Signal Component Forensics — 2026-08-07

Recorded: 2026-08-07 18:05:16 UTC

## Purpose

Preserve the first direct component-level view of recent Telegram-delivered BotA M15 signals and relate it to the current scoring implementation. This is diagnostic evidence only; it does not authorize a strategy mutation.

## Retained delivered-event component sample

Source: phone `logs/cron.signals.log` joined to positional columns in `logs/alerts.csv`.

Retained log produced:

```text
SENT_EVENTS_SINCE_2026_06_01=11
```

All 11 retained sent events were classified as `regime=trending`; observed ADX ranged from 26.2 to 40.6.

Eight of the eleven had `macd_comp=15.0`, the maximum MACD contribution. The two highest scores in the retained sample were:

```text
2026-06-17 EURUSD SELL score=85.20 RSI=17.2 RSI_COMP=15.0 MACD_COMP=15.0 ADX=29.9 ADX_COMP=8.0 H1=confirmed
2026-06-17 GBPUSD SELL score=87.50 RSI=21.2 RSI_COMP=15.0 MACD_COMP=15.0 ADX=35.8 ADX_COMP=10.0 H1=confirmed
```

The connected Supabase outcome records for the corresponding published signals show both closed at losses:

```text
EURUSD score~85 -> -15.8 pips
GBPUSD score~87 -> -19.2 pips
```

This is a small matched sample and is not sufficient by itself to change the model.

## Verified current score semantics

Current `tools/scoring_engine.sh` computes:

```text
base = 40
ema_comp = min(20, EMA separation in bps)
rsi_comp = min(15, abs(RSI - 50) * 0.6)
macd_comp = directional MACD histogram, capped at 15
adx_comp = monotonic trend-strength reward, capped at 10
plus Bollinger/session/volume/SR components
```

Important implication: once direction is SELL, progressively lower RSI values increase score until the full 15 points are awarded; once direction is BUY, progressively higher RSI values do the same. There is no exhaustion penalty for very oversold SELL entries or very overbought BUY entries in this component.

The score is therefore largely a trend/momentum-strength score, not independently calibrated evidence that the next M15 move has a high probability of reaching TP before SL.

## Pullback-width code observation

The same current source contains:

```text
# Pullback zone: price touches EMA21 (±0.3x ATR buffer)
pb_buffer = atr * 1.0
```

The implemented touch buffer is 1.0 ATR even though the nearby comment says ±0.3 ATR. The close test separately allows 0.3 ATR around EMA21. This comment/code mismatch is verified and may make the pullback admission zone substantially looser than the description implies.

This is a candidate entry-quality issue, not yet a proven performance defect.

## Current interpretation

The evidence now points away from a simple delivery-only fix. High scores can be produced by saturated momentum/trend components, including extreme RSI, and recent high-score signals can still lose. Therefore:

```text
REMOVE_COOLDOWN_NOW=NO
LOWER_TELEGRAM_MIN_SCORE_NOW=NO
LOWER_STRATEGY_SCORE_NOW=NO
WEAKEN_H1_NOW=NO
```

The next proof should use the existing local outcome ledger if available and join WIN/LOSS rows to the 25-column alert components. The goal is to compare winners vs losers for RSI extremity, MACD saturation, ADX, H1 state, session, EMA contribution, and score.

## Safety

```text
RECORDED_DATE=2026-08-07
PHONE_RUNTIME_MUTATION=NO
PRODUCTION_FILE_CHANGE=NO
SERVICE_ACTION=NO
PHONE_PROVIDER_CALL=NO
TELEGRAM_SEND=NO
SUPABASE_MUTATION=NO
STRATEGY_CHANGE=NO
```
