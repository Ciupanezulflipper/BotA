# BotA R1 — Owner/Restarter Contract

Date: **2026-08-10 UTC**
Status: **IMPLEMENTATION STAGED FOR REVIEW**
Scope: dummy runtime only.

## Purpose

R1 validates the minimal external owner/restarter independently of the trading engine and independently of production Android runtime mutation.

R1 does not integrate BotA market-data, watcher, closer, shadow, Telegram, Supabase, runit removal, cron removal, boot replacement, or strategy behavior.

## Files

```text
tools/bota_runtime_owner.py
tools/bota_dummy_runtime.py
tests/test_bota_runtime_owner.py
```

## Contract

The owner must:

1. hold exactly one non-blocking exclusive `flock` for ownership;
2. reject a second owner instance;
3. launch exactly one child runtime instance at a time;
4. provide the runtime with one generated `BOTA_RUNTIME_INSTANCE_ID` and one explicit heartbeat path;
5. observe actual persisted progress rather than PID existence alone;
6. allow startup grace before classifying a missing heartbeat as stale;
7. classify stale heartbeat as a living-zombie runtime;
8. terminate the entire runtime process group with `SIGTERM` followed by `SIGKILL` after a bounded grace period if required;
9. restart after child exit or zombie termination;
10. write durable owner events sufficient to prove start, exit, zombie detection, zombie termination, and bounded test completion;
11. require an explicit runtime command and therefore have no production BotA default target;
12. validate timing inputs as finite and bounded by type constraints.

## Dummy-runtime behaviors

The dummy runtime can:

- remain healthy and continuously write heartbeat progress;
- exit intentionally after a configured interval;
- intentionally stop heartbeat progress while remaining alive;
- expose controlled exit codes.

It contains no trading logic.

## R1 acceptance tests

Required automated tests:

```text
fresh heartbeat is healthy
missing heartbeat is stale
old heartbeat is stale
non-finite timeout configuration is rejected
runtime exit triggers restart
stale-but-live runtime triggers process-group termination and restart
second owner cannot acquire the owner flock
```

## Explicit exclusions

```text
PRODUCTION_PHONE_MUTATION=NO
TRADING_ENGINE_INTEGRATION=NO
TERMUX_BOOT_INSTALL=NO
RUNIT_REMOVAL=NO
CRON_REMOVAL=NO
PROFILE_D_CHANGE=NO
TELEGRAM_SIDE_EFFECT=NO
OANDA_SIDE_EFFECT=NO
SUPABASE_SIDE_EFFECT=NO
STRATEGY_CHANGE=NO
```

## Review gate

R1 remains non-deployable until exact-head automated tests, static checks, and human review pass.

After R1 passes, the next package is R2: lightweight Python orchestration against dummy bounded subprocess tasks and a richer useful-progress heartbeat. R2 still must not cut over production.
