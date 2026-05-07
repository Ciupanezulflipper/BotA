
## 2026-05-07T06:04:18Z — Bootlog: BotA ship-mode network/cache state

- Local timestamp: Thu May  7 16:04:18 AEST 2026
- UTC timestamp: Thu May  7 06:04:18 UTC 2026
- Watcher short SHA: ff1a040a835d
- Server-clock watcher patch: PRESENT
- Watcher syntax: PASS
- Code files replaced in this step: NO
- Strategy changed: NO
- Cache updated in this step: NO
- Runtime issue found: `crond` not running during audit.
- Cache issue found: M15 raw cache stuck at `2026-05-05T18:30:00Z`.
- Network nuance:
  - DNS resolution works in curl/Python.
  - TLS works.
  - Root provider endpoints may return HTTP 403/429.
  - Curl code 23 was likely caused by pipe/head truncation.
- Required next boot action:
  - Start crond.
  - Run manual updater.
  - Re-test watcher dry run.
