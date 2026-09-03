# BotA Operational Error Addendum — 2026-09-03

Purpose: preserve new failure classes discovered in the post-closure Android/Termux forensic audit.

Canonical detailed evidence: `audits/OPERATIONAL_RUNTIME_AND_DELIVERY_FORENSICS_2026-09-03.md`.

This addendum does not reopen strategy validation.

## OE001 — Manifest parity falsely labeled runtime parity

**Status:** PROVEN.

The Aug-16 Package-6 deployer verified SHA-256/mode only for a hard-coded 12-file MANIFEST and then emitted `RUNTIME_PARITY=PASS`.

The installed files had unresolved runtime dependencies outside that MANIFEST.

Prevention rule:

> A selected-file manifest matching its release is not proof that the installed runtime is executable as a dependency graph.

Required future distinction:

```text
MANIFEST_PARITY
DEPENDENCY_CLOSURE_PARITY
RUNTIME_BEHAVIOR_ACCEPTANCE
```

These are separate claims.

## OE002 — Shell helper deployed without required local script

**Status:** PROVEN.

`tools/run_signal_watcher_with_ledger.sh` was deployed from pinned release `f368363...` and invokes:

```text
tools/watcher_persistence_gate.py
```

The dependency existed in the pinned release but was omitted from Package-6 MANIFEST and absent on the phone.

Result during open-market cycles:

```text
python rc=2
Errno 2 / file not found
outer terminal=INTERNAL_ERROR
```

The outer aggregator also reported `aggregate=DATA_FETCH_FAILED`, which obscured the true error class.

Prevention rule:

> Every locally invoked executable/script path must be resolved and verified before deployment and after install.

## OE003 — Python guard deployed without imported module

**Status:** PROVEN AT CODE/MANIFEST LEVEL; RUNTIME IMPORT FAILURE OBSERVED.

`tools/telegram_send_guard.py` imports:

```python
from telegram_delivery import decision_matches, parse_message, row_dict
```

`tools/telegram_delivery.py` exists in pinned release `f368363...` but was omitted from the 12-file Package-6 MANIFEST.

Runtime errors contain repeated:

```text
ModuleNotFoundError: No module named 'telegram_delivery'
```

The canonical `telegram_send.sh` executes the guard before its network delivery boundary.

Prevention rule:

> Python local-import closure is a deployment dependency and must be verified exactly like directly executed scripts.

## OE004 — Terminal classification hid the underlying failure

**Status:** PROVEN.

The missing persistence helper produced Python rc=2, but the outer watcher evidence preserved `aggregate=DATA_FETCH_FAILED`.

This is semantically misleading: no data-fetch failure is required to produce the observed terminal state.

Prevention rule:

> Preserve low-level failure class alongside semantic aggregate. Never allow a generic aggregate to erase the exact process failure.

## OE005 — One retained cycle generalized to a multi-week period

**Status:** CORRECTED.

A retained Sep-2 cycle showed all three pairs rejected at score 0 / HOLD. That single sample was initially interpreted too broadly.

Full `logs/alerts.csv` audit proved after Aug-17:

```text
ROWS=3052
ACCEPTED=15
SCORE_NONZERO=694
BUY_SELL=694
```

Therefore post-Aug-16 strategy evaluation did not collapse universally to score 0.

Prevention rule:

> Use retained cycles as event evidence, not population evidence. Check the full ledger before making period-wide claims.

## OE006 — Accepted decision mistaken for delivered signal

**Status:** DURABLE PREVENTION RULE.

For the pinned watcher path:

```text
filter accepted
 -> score/tier gate
 -> cooldown
 -> dedup
 -> Telegram send
 -> transaction completion
 -> GREEN-only Supabase publish
```

An accepted `alerts.csv` row is not proof of Telegram delivery or Supabase publication.

## OE007 — Clock quorum looked more independent than it was

**Status:** ARCHITECTURAL WEAKNESS; NOT INCIDENT ROOT CAUSE.

Google, OANDA, Yahoo and Cloudflare HTTPS Date responses agreed and were correct during the Sep-3 test. However, all observations traversed one phone/network path.

Prevention rule:

> Distinguish independent remote authorities from independent observation paths.

The current gate result was correct; the architecture still deserves this caveat.

## OE008 — Device local time contaminated display timestamps

**Status:** PROVEN / MITIGATED BY TRUSTED SERVER EPOCH.

The phone wall clock was approximately 14 hours fast. `started` watcher rows used local display UTC while terminal rows used server epoch, making events from the same cycle appear many hours apart unless the time source was read.

Prevention rule:

> Every operational timestamp must carry an explicit authoritative time source; local display time must never be compared directly to trusted server-epoch time.

## Current forensic boundary

Do not repair the phone runtime until the 15 post-Aug-17 accepted rows have been correlated to their delivery outcomes.

No item in this addendum authorizes strategy tuning, strategy reopening, or Production cutover.
