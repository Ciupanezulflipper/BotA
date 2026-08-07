# BotA Historical Acquisition Salvage — 2026-08-07

This directory is the focused current-`main` salvage of the proven acquisition concepts from draft PR #6.

It exists for one purpose: acquire an immutable, replay-grade OANDA candle dataset for the half-open interval `2026-06-01T00:00:00Z` through `2026-07-11T00:00:00Z` without touching BotA's live candle cache, strategy, Telegram, Supabase, services, or runtime state.

## Scope

- Instruments: `EUR_USD`, `GBP_USD`
- Granularities: `M15`, `H1`, `H4`, `D`
- Provider: OANDA
- Price component: midpoint (`price=M`)
- Completed candles only
- Default historical interval: `[2026-06-01T00:00:00Z, 2026-07-11T00:00:00Z)`

## Safety properties

- Preview is no-network.
- Live acquisition requires `--execute`, the exact authorization phrase, and an ephemeral `BOTA_AUDIT_OANDA_TOKEN`.
- The token is never persisted.
- The OANDA host is allowlisted.
- Requests use explicit `from`/`to`; `count=` is prohibited.
- Output must be outside the BotA repository.
- The output root must be new or empty.
- Raw responses, redacted metadata, canonical CSVs, and the manifest are write-once.
- Every artifact in `manifest.json` is SHA-256 indexed.
- `verify` detects later size/hash tampering.
- No production BotA module is imported or executed.

## Preview

```bash
python -m audit.historical_acquisition_20260807.acquire preview \
  --output-root "$HOME/bota-forensics/bota-20260601-20260711"
```

The preview must report `mode=dry_run_no_network`, `network_permitted=false`, eight requests under the default 2-pair × 4-timeframe scope, and no `count=` query parameter.

## Live read-only acquisition

Do not place the token in a command argument, file, screenshot, GitHub, or chat.

```bash
read -s BOTA_AUDIT_OANDA_TOKEN
export BOTA_AUDIT_OANDA_TOKEN

python -m audit.historical_acquisition_20260807.acquire acquire \
  --output-root "$HOME/bota-forensics/bota-20260601-20260711" \
  --execute \
  --authorization-phrase I_AUTHORIZE_READ_ONLY_OANDA_ACQUISITION

unset BOTA_AUDIT_OANDA_TOKEN
```

## Integrity verification

```bash
python -m audit.historical_acquisition_20260807.acquire verify \
  --output-root "$HOME/bota-forensics/bota-20260601-20260711"
```

A valid untouched dataset returns `status=PASS`.

## What this package does not prove

Successful acquisition does not prove the strategy is good, does not prove missed signals, and does not approve any threshold or H1/ADX change. The next stage after a verified dataset is deterministic replay through a production-parity signal path.
