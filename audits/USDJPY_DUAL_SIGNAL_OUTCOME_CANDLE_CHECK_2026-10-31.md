# BotA USDJPY dual-signal outcome check — 30 October 2026

Recorded: 31 October 2026. Scope: read-only production evidence reconciliation; **not** proof of broker fills, spread, or OANDA-origin data. No BotA strategy/config, Supabase records, or runtime files were changed.

## Sources and identity
- ProfitLab Supabase project `ozgkeslgjqbqfewojnmr`, `public.signals` and `public.shadow_log`, queried 31 October 2026.
- Production Hetzner retained M15 OHLC file: `/var/lib/bota/data/candles/USDJPY_M15.csv`, read via SSH on 31 October 2026; header `time,open,high,low,close`. File covered 26–30 October (468 rows plus header).
- **Provenance limitation:** Production control record identifies primary provider as **YAHOO**. The historical-replay acquisition script supports OANDA midpoint candles, but this does **not** establish that this specific live CSV originated from OANDA. Consequently these are *retained production-cache OHLC* checks, **not** independently re-fetched original OANDA candles or bid/ask/tick verification.
- Timestamps UTC. M15 rows are opening timestamps; a 14:00 row covers 14:00–14:15.

## Independently distinct signal rows

| Field | Signal A | Signal B |
|---|---|---|
| signal id | `0749c824-ce56-4ad7-858a-5a9f14255140` | `f8637fdf-0ab9-4b0f-80fe-5959fd9bfe13` |
| pair / direction | USDJPY / SELL | USDJPY / SELL |
| created UTC | 2026-10-30 11:30:04.861164 | 2026-10-30 11:46:01.143813 |
| entry | 157.07100 | 157.09801 |
| stop loss | 157.36614 | 157.38907 |
| take profit | 156.48072 | 156.51589 |
| current Supabase status | CLOSED | CLOSED |
| recorded result | -29.50 pips | -29.10 pips |
| Supabase closed_at | 14:15 UTC | 16:00 UTC |
| two shadow policies | STATIC_MIRROR and BE_1.0R | STATIC_MIRROR and BE_1.0R |
| both shadow outcomes | CLOSED_SL | CLOSED_SL |
| shadow_closed_at | 14:00 UTC | 15:45 UTC |
| highest_mfe_pips | 10.9 | 13.6 |
| arm_triggered | false | false |
| shadow last_error | null | null |

## OHLC crossings from the retained server file

Signal A: the 14:00 M15 row = O 157.29600525, H **157.37600708**, L 157.12399292, C 157.15400696. H exceeds SELL stop 157.36614. Earlier retained candles from the signal's creation window through 13:45 did not reach stop or TP. Production close at 14:15 corresponds to end of 14:00 M15 candle.

Signal B: the 15:45 M15 row = O 157.21200562, H **157.50999451**, L 157.18800354, C 157.47300720. H exceeds SELL stop 157.38907. Earlier retained candles from creation through 15:30 did not reach stop or TP. Production close at 16:00 corresponds to end of 15:45 M15 candle.

The recorded pip results agree with SELL entry-minus-stop calculations rounded to tenths: A (157.07100−157.36614)×100 = -29.514; B (157.09801−157.38907)×100 = -29.106. Both `shadow_log.actual_pips` values equal `signals.result_pips`.

## Assessment and boundaries

**PASS, retained-cache OHLC:** Both distinct IDs exist in production, both SL prices are reached in their respective closing M15 bars, neither TP was reached earlier in the inspected cached bars, and both reported pip losses are numerically consistent. The systematic 15-minute shadow-versus-production close offset agrees with opening-stamped completed candles; no timestamp defect is demonstrated.

**NOT PROVEN:** Original OANDA provenance; independent OANDA historical pull; bid/ask spreads; tick path, slippage or broker fill price; end-to-end Telegram exact-identity retry deduplication.

**Exact-dedup gate:** The natural overlap candidate is evidenced by the two distinct IDs and creation/close windows, but overall end-to-end exact-dedup acceptance remains OPEN until individual delivery records and same-ID retry dedup evidence are verified. Do not infer that candle outcome validation closes this separate gate.

No remediation or P&L reclassification is justified by the inspected OHLC evidence; keep both recorded losses. Do not modify signals or trading strategy.
