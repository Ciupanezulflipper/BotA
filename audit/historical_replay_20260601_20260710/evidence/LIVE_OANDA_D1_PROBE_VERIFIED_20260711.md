# Live OANDA D1 Probe — Verified 2026-07-11

## Classification

- [proven] A bounded, read-only OANDA practice-endpoint probe completed successfully for `EUR_USD` with granularity `D`.
- [proven] The probe used explicit `from` and `to` parameters and did not use `count`.
- [proven] The token was supplied through the ephemeral environment variable `BOTA_AUDIT_OANDA_TOKEN` and was unset after execution.
- [proven] The local verification step executed without loading the token and without making an additional provider request.

## Run identity

- [proven] Run ID: `oanda-probe-eurusd-d-20260711-v1`
- [proven] Interval requested: `2026-07-01T00:00:00Z` to `2026-07-11T00:00:00Z`
- [proven] Endpoint class: OANDA practice
- [proven] Instrument: `EUR_USD`
- [proven] Granularity: `D`
- [proven] Response status: `200`
- [proven] Raw candle count: `8`
- [proven] Derived candle count: `8`
- [proven] Manifest schema version: `1`
- [proven] Offline verification exit code: `0`

## Observed daily timestamps

- [proven] `2026-06-30T21:00:00.000000000Z`
- [proven] `2026-07-01T21:00:00.000000000Z`
- [proven] `2026-07-02T21:00:00.000000000Z`
- [proven] `2026-07-05T21:00:00.000000000Z`
- [proven] `2026-07-06T21:00:00.000000000Z`
- [proven] `2026-07-07T21:00:00.000000000Z`
- [proven] `2026-07-08T21:00:00.000000000Z`
- [proven] `2026-07-09T21:00:00.000000000Z`

- [proven] Every returned daily candle had `complete=True`.
- [inferred] OANDA daily candles in this probe align at `21:00:00Z`, not UTC midnight.
- [inferred] The inclusion of `2026-06-30T21:00:00Z` for a request starting at `2026-07-01T00:00:00Z` is consistent with OANDA returning the daily candle whose interval contains the requested start instant.

## Artifact hashes

- [proven] Raw artifact SHA256: `0d24a5d884059001d360322d5727adceaeb5a861825b4c43adaf58925cb964f0`
- [proven] Request metadata SHA256: `920ed586fe719b2f71cef01aff8a576a7b2e17d096b5a8b0d8003330f687f416`
- [proven] Response metadata SHA256: `2aea5e75d4295fd0e0164030beca54d588990a724baf99b2a96a9bda91c363e9`
- [proven] Derived candles SHA256: `9e34e5690fa0e721fd9feefedc4048bdd73c2aec3919a41d4ac94561f7dbfa7b`
- [proven] Manifest SHA256: `55a3525fc47fed049f4545cd08e97496e9395f7f568953a7773c3374c4ae6661`
- [proven] Artifact index SHA256: `d8d2d5657a18a7c80824521bf4ae28727c7b28c12a34474524c74323026b63d8`

## Boundaries and remaining gaps

- [proven] This probe verifies only one bounded EUR_USD daily interval.
- [not proven] Full replay-window D1 coverage is not yet verified.
- [not proven] GBP_USD daily coverage is not yet verified.
- [not proven] Independent-provider agreement is not yet verified.
- [not proven] Exact production D1 availability semantics remain to be reconciled with the point-in-time replay rules.
