# Live OANDA H4 probe verification — 2026-07-11

Status: proven

Run ID: `oanda-probe-eurusd-h4-20260711`

Scope:
- instrument: `EUR_USD`
- granularity: `H4`
- requested interval: `2026-07-09T00:00:00Z` to `2026-07-11T00:00:00Z`
- provider endpoint class: OANDA practice
- price component: midpoint (`M`)
- request form: explicit `from`/`to`; no `count` parameter
- execution location: isolated historical-replay worktree
- production BotA checkout unchanged by this verification step

Offline verification result:
- required evidence files present: YES
- raw JSON valid: YES
- raw instrument: `EUR_USD`
- raw granularity: `H4`
- raw candle count: `12`
- derived candle count: `12`
- response status: `200`
- count parameter present: NO
- manifest run ID matched: YES
- manifest schema version: `1`
- H4 offline verification passed: YES
- verification exit code: `0`
- token loaded during verification: NO
- provider request executed during verification: NO

Observed candle range:
- first candle time: `2026-07-08T21:00:00.000000000Z`
- last candle time: `2026-07-10T17:00:00.000000000Z`

Artifact hashes:
- raw: `41e145960bb98fac8875711b7d47a9557f5bc8ded0118bfd8dfe394c076e2e4b`
- request metadata: `37b4dff35df625c85f55897a7e48ffa3c888540ee002978027eb56364ba6b77a`
- response metadata: `2ea0cd54a9c0e7ebffaec4f20d1b1bc45f0940a9c47b305f657df77de63dc5a8`
- derived candles: `2ced1ab342ae661b70ff89962b7026d9d7d68e710ec67a51a0823ac17dc85865`
- manifest: `81a0c5c0b161523065c2658d81c2692d4f89786f2ba7f3b852575b1c85c36f6d`

Claim boundaries:
- Proven: one bounded EUR_USD H4 probe produced a complete local evidence set that passed offline structural verification.
- Not proven: full-period provider retention, entitlement across all requested instruments/timeframes, independent-provider agreement, production alignment semantics, or complete historical replay correctness.
