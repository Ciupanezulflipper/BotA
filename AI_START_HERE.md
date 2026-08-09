# BotA AI Start Here

Last updated: **2026-08-09 UTC**

Read this before proposing BotA commands, code, service, strategy, Telegram, provider, Supabase, replay, deployment, or Android/Termux changes.

## Current authoritative truth

```text
GITHUB_MAIN_AT_PACKAGE1_DEPLOYMENT=8728de6b5a2ed0f4647374ef4fa6ed72f9eb03c0
PHONE_DEPLOYED_RELEASE=8728de6b5a2ed0f4647374ef4fa6ed72f9eb03c0
DEPLOYED_TO_PHONE=PASS
RUNTIME_FILE_PARITY=PASS
ACTIVE_RUNIT_WRAPPER=PASS
ACTIVE_RUNIT_WRAPPER_MODE=755
THREE_PAIR_RUNTIME_SCOPE=PASS
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
TELEGRAM_ENABLED=1
DRY_RUN_MODE=0
PACKAGE_1_CLOCK_SESSION=PASS
CURRENT_CONTROL_PLANE=HEALTHY
CURRENT_REQUIRED_SERVICES_OWNED=7/7
CURRENT_REQUIRED_SERVICES_RUNNING=7/7
CURRENT_ORPHANED_RUNSV=0
CURRENT_DUPLICATE_SERVICE_ROWS=0
CURRENT_LIVE_CROND_COUNT=1
ACTIVE_WATCHER_CRON=0
ACTIVE_PROFITLAB_CRON=1
PROFITLAB_CURSOR_PRESERVED=PASS
LIVE_CLOSED_MARKET_CYCLE=PASS
PERSISTENT_WATCHDOG_HARDENING=PENDING
PRE_MARKET_PRODUCTION_INTEGRITY=PENDING
OPEN_MARKET_THREE_PAIR_LIVE_PROOF=PENDING
MONDAY_READY=NO
```

BotA has completed **Package #1 — Clock & Session Time** and the present control plane has been repaired to a clean 7/7 single-manager topology. It is not yet Monday-ready because Package #2 persistent recovery/pre-market integrity and the genuine open-market three-pair proof remain outstanding.

## Package #1 — completed and live-proven

PR #84 bound strategy/event time to one trusted server epoch per watcher cycle.

Deployed runtime files:

```text
tools/calendar_guard.py
tools/market_open.sh
tools/news_filter_real.py
tools/scoring_engine.sh
tools/trusted_time.py
```

Key fixed failure classes:

- session score no longer depends on Android wall clock;
- nested market gates reuse inherited `BOTA_SERVER_EPOCH`;
- economic-calendar distance uses trusted epoch;
- Finnhub calendar date uses trusted epoch when active;
- pre-existing calendar before/after exclusion-window sign bug corrected;
- CLOCK_BOOTTIME/monotonic remains the elapsed-time/cooldown domain.

Validation included deterministic boundary tests, real scorer integration, no-network inherited-clock tests, ShellCheck/Python compile, cloud regression, and a 2,000-case seeded time/timezone fault matrix.

Latest live Package #1 proof:

```text
cycle_id=b32a66a6-1a91-4b61-b759-c32851cbae6b:144452448476926
terminal_outcome=MARKET_CLOSED
market_reason=MARKET_CLOSED_SUNDAY
time_source=server_epoch
server_epoch=1786245830
timestamp_utc=2026-08-09T03:23:50+00:00
```

No score threshold, pair scope, wrapper, crontab, or ProfitLab state was changed by Package #1.

## Package #2 — live incident repaired, engineering hardening pending

The first Package #1 deploy attempt safely aborted before mutation because `crond` appeared down. Forensics proved the real condition was more subtle:

```text
current manager PID=4398
current runsv crond PID=24583
stale live crond PID=4107
stale crond parent=1
stale crond held $PREFIX/var/run/crond.pid
replacement crond attempts failed every ~1s on pidfile lock
```

The stale daemon was identity-checked and terminated; runit then started exactly one replacement:

```text
new crond PID=17994
new crond parent runsv=24583
live crond count=1
crond stability=PASS
```

The same incident exposed six surviving PID-1-orphaned BotA `runsv` supervisors. Final reconciled topology:

```text
manager_count=1
manager_pid=4398
owned=7/7
running=7/7
orphaned=0
duplicate_service_rows=0
```

Important: this is a **successful live repair**, not completion of Package #2. The phone boot launcher still explicitly disables persistent recovery (`RUNSVDIR_GUARD_START=DISABLED`). The watchdog source matches GitHub and a one-shot healthy-topology run passed, but persistent boot/runtime recovery and the exact stale-live-singleton-child case still require reviewed hardening and fault-injection tests.

## Phone deployment model

The Android Git checkout remains intentionally separate from runtime identity:

```text
PHONE_LOCAL_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_LOCAL_HEAD=4339543551aae2e2bcbf727aefe96e3eb103b665
```

Do not infer production version from the phone worktree HEAD. Production identity is the verified bounded runtime manifest from the immutable approved GitHub commit.

Active watcher wrapper:

```text
/data/data/com.termux/files/home/.config/bota-sv/bota-watcher/run
blob=25b240dc6913bf9cde82ab79a62ea6cddd73bc8e
mode=755
```

## ProfitLab state

```text
cursor_offset=897734
alerts_csv_size=897734
pending_bytes=0
```

Do **not** run `profitlab_delivery.py --bootstrap` on the current production state.

## Current strategy scope

```text
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
POLICY_B_ENABLED=1
POLICY_B_SCORE_MIN=70
POLICY_B_ADX_MAX=30
NEWS_ON=0
```

Do not loosen score, ADX, H1/H4/D1, Telegram, cooldown, or eligibility rules to manufacture signals.

## Read first

1. `CONTINUITY_CURRENT.md` — current status and exactly one next engineering action.
2. `audits/PACKAGE1_CLOCK_AND_PACKAGE2_CONTROL_PLANE_2026-08-09.md` — immutable Package #1 deployment proof and Package #2 incident/recovery record.
3. `audits/PHONE_DEPLOYMENT_WEEKEND_PROOF_2026-08-09.md` — earlier immutable deployment/runtime proof.
4. `ANDROID_TERMUX_TOOLCHAIN.md` — Android/Termux engineering-tool baseline and usage boundaries.
5. `DECISIONS.md` and `ERRORS.md` — current locked decisions and failure/prevention register.
6. `docs/FORENSIC_OPERATING_MODEL.md` — connector-first operating model.

Older dated audits remain evidence. Current-state files may supersede their operational status but must not rewrite historical results.

## Mandatory source hierarchy

```text
GitHub connector   -> code, commits, PRs, docs, tests
Supabase connector -> published signal/outcome/database truth
Phone/Termux       -> runtime-only state, credentials, local persistent state/results
```

## Deployment and service discipline

Never equate:

```text
CODE_READY
MERGED_TO_MAIN
DEPLOYMENT_READY
DEPLOYED_TO_PHONE
RUNTIME_PARITY_VERIFIED
LIVE_PIPELINE_VERIFIED
PRE_MARKET_PRODUCTION_INTEGRITY
MONDAY_READY
```

Production process health must separately prove **running** and **correct ownership**. A live stale daemon or PID-1-orphaned supervisor is not healthy merely because work is still happening.

For production deployment/recovery:

- pin an immutable GitHub SHA;
- verify exact file blobs and executable modes;
- back up overwritten runtime files/config;
- preserve logs, state, untracked evidence, ProfitLab cursor, and unrelated cron;
- keep exactly one native `runsvdir` manager;
- require all seven service supervisors to be owned by that manager;
- distinguish stale live singleton/resource owners from stale pidfiles with dead processes;
- restart only the component that must change;
- require post-change runtime evidence;
- rollback or stop when topology/release invariants fail.

Never push directly to `main`. Use branch -> verified changes -> PR -> exact-head gates -> merge -> separate deployment gate when runtime files changed.

## Current freeze

```text
DO_NOT_BOOTSTRAP_PROFITLAB=YES
DO_NOT_LOWER_THRESHOLDS=YES
DO_NOT_FORCE_SIGNAL_COUNT=YES
DO_NOT_FORCE_TELEGRAM_TEST_SIGNAL=YES
DO_NOT_DECLARE_PACKAGE2_COMPLETE_FROM_LIVE_REPAIR=YES
DO_NOT_DECLARE_MONDAY_READY_FROM_WEEKEND_PROOF=YES
```

## Exactly one next engineering action

Complete **Package #2 — Pre-Market Production Integrity** before another production mutation. Audit and fault-inject the native manager/watchdog/boot/recovery path, including PID-1 orphan handoff, down-service recovery, dead stale pidfile, duplicate supervisor, and the exact `manager-owned runsv + stale live singleton child/resource owner` condition seen with `crond`. Add immutable release/config/data-path readiness checks. Only after reviewed tests pass should the persistent watchdog/boot behavior be changed on the phone.

After Package #2 passes, the final production-readiness gate is the first genuine `MARKET_OPEN` cycle proving EURUSD:M15, GBPUSD:M15, and USDJPY:M15 in the same current cycle with fresh updater/shadow/data evidence, one authoritative terminal outcome, trusted time, and unique ownership. Three legitimate rejects are acceptable; Telegram delivery is not required.