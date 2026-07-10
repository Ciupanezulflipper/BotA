# BotA Historical Replay Sidecar

[proven] This directory is an isolated forensic sidecar for the half-open interval `2026-06-01T00:00:00Z` through `2026-07-11T00:00:00Z`.

## Safety contract

- [proven] No production BotA module may be imported or executed.
- [proven] No file outside this directory may be written.
- [proven] Telegram and Supabase access are prohibited.
- [proven] Secrets must not be committed.
- [proven] Raw provider artifacts are never normalized in place.
- [proven] Derived outputs must be written under `derived/` or `evidence/`.
- [proven] The first implementation increment uses synthetic fixtures only.

## Scope

- [proven] Pairs: EURUSD, GBPUSD.
- [proven] Execution timeframe: M15.
- [proven] Context timeframes: H1, H4, D1.
- [proven] Primary provider contract: OANDA midpoint candles with complete candles only.
- [proven] Historical thresholds: filter 65, Telegram 70, GREEN 75.
- [proven] Active market gate: Monday-Friday, 07:00-20:00 UTC.

## Initial modules

- `src/path_guard.py`: realpath containment and symlink rejection.
- `src/manifest.py`: deterministic SHA-256 artifact manifests.
- `src/oanda_contract.py`: request-contract validation without network access.
- `src/validate_fixture.py`: synthetic candle validation.

## Non-goals for this increment

- [proven] No live provider download.
- [proven] No replay of production strategy code.
- [proven] No notification or database publication.
- [proven] No production deployment.
