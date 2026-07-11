# Live OANDA EUR_USD H1 probe verification — 2026-07-11

- [proven] Run ID: `oanda-probe-eurusd-h1-20260711-v1`.
- [proven] Execution environment: isolated historical-replay worktree, not production BotA.
- [proven] Provider endpoint: OANDA practice, read-only candles.
- [proven] Instrument: `EUR_USD`.
- [proven] Granularity: `H1`.
- [proven] Requested interval: `2026-07-09T00:00:00Z` through `2026-07-11T00:00:00Z`.
- [proven] Live acquisition exit code: `0`.
- [proven] Response status: `200`.
- [proven] Raw candle count: `45`.
- [proven] Derived candle count: `45`.
- [proven] Incomplete candle count: `0`.
- [proven] First candle time: `2026-07-09T00:00:00.000000000Z`.
- [proven] Last candle time: `2026-07-10T20:00:00.000000000Z`.
- [proven] Request did not include a `count` parameter.
- [proven] Manifest run ID matched the requested run ID.
- [proven] Manifest schema version: `1`.
- [proven] Offline verification exit code: `0`.
- [proven] Token alias was unset after acquisition.
- [proven] Token value was not printed.

## Artifact hashes

- [proven] Raw: `3cb25808f0a7aa399123f3ea4bf52ea95ca66c3b8333451d9f194452e92fa10a`.
- [proven] Request metadata: `623ad1fd8fe6aa2f31eb92439af11049a798e44494d5b1f51b62b02242560400`.
- [proven] Response metadata: `db6730d6680ab5ba40cd539c0fd7f98eb877e54f7962dd857724bff1f7c08145`.
- [proven] Derived candles: `06245cd16f9b4313ba56550674539b28ad2027b8fe6270320efb2885afc33be0`.
- [proven] Manifest: `37d8753463662dd0e8cc91f070225c0165250091e2ea6c6cc034939c6e11929e`.

## Production-parity mapping

- [proven] Production BotA uses H1 as a context timeframe in the active M15 fusion path.
- [proven] This probe establishes provider-level H1 cadence and complete-candle behavior for the replay sidecar.
- [not proven] Exact semantic equivalence between replay H1 visibility and production H1 consumption remains to be demonstrated against the production fusion and cache contracts.
- [proven] This evidence must not be treated as proof that the sidecar is production-equivalent by itself.
