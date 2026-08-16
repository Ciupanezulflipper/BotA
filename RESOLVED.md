# BotA Resolved Issues

## 2026-04-21 / 2026-04-22

### Yahoo 429 retry storm
- Status: RESOLVED
- Root cause:
  - Yahoo fallback could return 429 and updater retried generic non-zero exits
- Fix:
  - `tools/data_fetch_candles.sh` exits with code `3` on Yahoo 429
  - `tools/indicators_updater.sh` stops retrying on rc=3
- Proof:
  - syntax checks passed
  - fetch/build flow recovered

### phase=Unknown contract mismatch
- Status: RESOLVED
- Root cause:
  - `tools/market_open.sh` emitted descriptive strings
  - `tools/scoring_engine.sh` accepted only exact `Open` or `Closed`
- Fix:
  - `tools/market_open.sh` now emits exact `Open` or `Closed`
- Proof:
  - scorer moved from `phase=Unknown` to `market phase Closed`

### stale watcher lock regression
- Status: RESOLVED
- Root cause:
  - stale watcher lock blocked live watcher execution
- Fix:
  - stale lock detection/removal proven in watcher output
- Proof:
  - watcher resumed and executed `--once` runs successfully

## 2026-05-27

### Step 6 daily pulse wrapper implementation + first private live send
- Status: RESOLVED (wrapper and first send proven — cron rollout still open/not active)
- What was proven:
  - `tools/run_daily_pulse.sh` built with dedup gate and `--dry-run` support.
  - First private live send: `LIVE_SEND_EXIT_CODE=0`, `telegram_sent=True`, `supabase_published=False`.
  - Dedup file `state/daily_pulse_sent_2026-05-27.ok` created correctly.
  - Layout cleanup: heavy separator bars removed; mobile-friendly two-line-per-pair format confirmed.
  - `--dry-run` skips correctly when dedup file present.
- Step 6 commit: `6aa985e`, tag: `step-6-wrapper-gates-2026-05-27`
- Layout cleanup commit: `65d1137`
- Branch: `main`, pushed to `origin/main`.
- Cron: NOT active. Manual sends only at this stage.
- Main BotA channel: NOT approved.
- Remaining gate: 3 successful private daily sends before cron/main channel decision.
- Production trading behavior changed: NO.
- Strategy changed: NO.
- H1 logic changed: NO.
- Thresholds changed: NO.
- Supabase publish for Market Pulse: NO (remains false).
- ProfitLab executable signal behavior: UNCHANGED.

### Step 5 private Telegram Market Pulse send
- Status: RESOLVED
- What was proven:
  - `tools/product_message_v1.py --send --chat-id <TEST_CHAT_ID>` delivered message to private test chat.
  - `telegram_sent=True` confirmed in log and stdout.
  - `supabase_published=False` confirmed.
  - Shadow mode continues working: `telegram_sent=False`, `supabase_published=False`.
  - macro6=3 neutral/default no longer displayed as "macro filter active".
  - Market Pulse contains no entry, SL, or TP.
  - Market Pulse disclaimer present.
- Commit: `274b0d3`
- Tag: `step-5-private-send-confirmed-2026-05-27`
- Branch: `main`, pushed to `origin/main`.
- Production trading behavior changed: NO.
- Strategy changed: NO.
- H1 logic changed: NO.
- Thresholds changed: NO.
- Cron changed: NO.
- Supabase publish for Market Pulse: NO (remains false).
- ProfitLab executable signal behavior: UNCHANGED.

---

## 2026-07-10 — Watcher pre-journal dedup observability defect

<!-- BOTA_OBSERVABILITY_V4_2026_07_10 -->

- Status: RESOLVED
- [proven] Root cause: content dedup executed before `alerts.csv` journaling and wrote hash state before confirmed Telegram delivery.
- [proven] Fix: journal every completed parsed decision before rejection and Telegram delivery gates.
- [proven] Fix: split delivery hash calculation, read-only comparison, and post-success marking.
- [proven] Fix: update delivery hash only after successful real Telegram send.
- [proven] Static validation: PASS.
- [proven] Atomic deployment: PASS.
- [proven] Natural cron-cycle validation: PASS.
- [proven] Natural proof wrote two rejected HOLD rows while preserving both delivery hashes and both `last_sent` files.
- [proven] Installed watcher SHA-256: `b8a3adf46582e3a69d5b22d12a4da070bc8be2ceff76a4aa99e9d6c96544a9ef`.
- [proven] Strategy and production selection rules changed: NO.
- [not proven] Whether any valid signal was missed during the historical June outage remains unresolved.

---

## 2026-08-09 — Package #1 Clock & Session Time

### Android wall-clock leakage into strategy/event semantics
- Status: **RESOLVED / DEPLOYED / LIVE-PROVEN**
- Release: `8728de6b5a2ed0f4647374ef4fa6ed72f9eb03c0`
- PR: #84
- Root causes fixed:
  - scorer session component could use Android wall clock;
  - nested market gates could establish a different `now` from the outer watcher cycle;
  - economic-calendar distance used wall clock;
  - active Finnhub date selection used wall clock;
  - economic-calendar before/after signed windows were reversed.
- Fix:
  - one inherited `BOTA_SERVER_EPOCH` controls market/session/calendar/news event-time semantics;
  - CLOCK_BOOTTIME/monotonic remains elapsed-time/cooldown domain;
  - signed calendar boundaries corrected.
- Validation:
  - deterministic trusted-time boundaries PASS;
  - no-network inherited-epoch market boundaries PASS;
  - real scorer session-boundary integration PASS;
  - ShellCheck/Python compile PASS;
  - 2,000-case seeded time/timezone fault matrix PASS.
- Live proof:
  - cycle `b32a66a6-1a91-4b61-b759-c32851cbae6b:144452448476926`;
  - `MARKET_CLOSED / MARKET_CLOSED_SUNDAY`;
  - `time_source=server_epoch`;
  - `server_epoch=1786245830`.
- Strategy thresholds changed: NO.
- Pair scope changed: NO.
- ProfitLab cursor changed: NO.

## 2026-08-09 — Package #2 live control-plane repairs

### Stale live `crond` singleton owner
- Status: **LIVE INCIDENT RESOLVED**
- Root cause:
  - old live `crond` PID `4107`, PPID `1`, still held `$PREFIX/var/run/crond.pid`;
  - current manager-owned `runsv crond` PID `24583` retried a second daemon every ~1 second;
  - each replacement failed to lock the pidfile.
- Repair:
  - verified stale daemon PID/command/parent;
  - quiesced failed restart loop;
  - terminated only PID 4107;
  - current runsv started replacement PID `17994`;
  - verified replacement PPID `24583`, one live `crond`, and stability.
- Crontab changed: NO.
- Bot runtime files changed by repair: NO.
- ProfitLab state changed: NO.

### PID-1-orphaned BotA `runsv` supervisors
- Status: **LIVE TOPOLOGY RESOLVED**
- Discovered state:
  - `running=7/7`;
  - `owned=1/7`;
  - `orphaned=6`.
- Final repaired state:
  - manager count `1`;
  - `owned=7/7`;
  - `running=7/7`;
  - `orphaned=0`;
  - duplicate service rows `0`.

Canonical incident evidence: `audits/PACKAGE1_CLOCK_AND_PACKAGE2_CONTROL_PLANE_2026-08-09.md`.

## 2026-08-09 — Package #2 finalization, PR #87/#88 deploy, and pre-market proof

Status: **RESOLVED / DEPLOYED / NATURALLY PROVEN / PRE-MARKET GATE PASS**

Verified phone acceptance:

```text
PACKAGE_2_FINALIZER_DEPLOY=PASS
CURRENT_CONTROL_PLANE=HEALTHY_AT_PROOF_TIME
CURRENT_REQUIRED_SERVICES_OWNED=7/7
CURRENT_REQUIRED_SERVICES_RUNNING=7/7
CURRENT_ORPHANED_RUNSV=0
CURRENT_DUPLICATE_SERVICE_ROWS=0
WATCHDOG_SINGLETON=PASS
BOOT_PERSISTENCE=PASS
PR87_PR88_PHONE_DEPLOY=PASS
RUNTIME_DEPENDENCY_CONTRACT=PASS
REQUESTS_VERSION=2.34.2
PIP_BASELINE_REGRESSION=NO
PROFITLAB_PRESERVED=PASS
NATURAL_SHADOW_CYCLE=PASS
PRE_MARKET_PRODUCTION_INTEGRITY=PASS
```

These are historical phone proofs from 2026-08-09. They are not a substitute for rechecking current phone state when current runtime truth is required.

Canonical proof: `audits/PRE_MARKET_READINESS_CHECKPOINT_2026-08-09.md`.

---

## 2026-08-09 — PR #89 watchdog persistence guardian

- Status: **RESOLVED AT REPOSITORY LEVEL / MERGED**
- PR: #89
- Merge commit: `741a2756675a789dc23ab7d6df3b2675bc474fd6`
- Correction recorded 2026-08-13: older continuity files still described PR #89 as open/current blocker after it had merged.
- Current implication: PR #89 is **not** the active blocker.

Any statement that PR #89 is currently open or the current readiness blocker is stale.

---

## 2026-08-13 — Documentation placeholder create/revert incident

- Status: **RESOLVED / NO CONTENT DRIFT**
- During audit recording, an audit placeholder was accidentally created on protected `main` before the intended docs branch existed.
- The placeholder was immediately deleted.
- GitHub rejected force-reset of protected `main`, leaving a create+revert pair in history.
- Direct compare:

```text
BASE=3e69920582d3d310be751e7b451f1afb67e1e5bb
HEAD=3cf3dd1470e4dff7ec4e4d4d7b32f8eb57e9c022
FILES_CHANGED=0
```

- Runtime/strategy content drift: **NONE**.
- Prevention rule added to `ERRORS.md`: create/verify the target branch before any content write; never rely on default-branch fallback.

---

## Still not resolved after the 2026-08-13 audit

The following are explicitly **not** resolved and must not be listed as PASS:

```text
PR108_EXACT_HEAD_CI=FAIL
PR108_CURRENT_HEAD_REVIEW=NOT_COMPLETE
SONARCLOUD_SECURITY_RATING_NEW_CODE=D
SECURITY_WORKFLOW_FALSE_GREEN_CLASS=OPEN
GITLEAKS_SENSITIVE_PATH_BLIND_SPOT=OPEN
PROVIDER_LIMITS_SHALLOW_COPY_ALIASING=OPEN
HISTORICAL_CREDENTIAL_ROTATION_STATUS=UNPROVEN
CURRENT_VALID_PR108_PHONE_PACKAGE=NO
PR102_DO_NOT_DEPLOY=YES
PR108_DEPLOYED=NO
PR108_RUNTIME_VERIFIED=NO
PR108_LIVE_THREE_PAIR_PATH_VERIFIED=NO
```

Canonical current audit: `audits/READ_ONLY_ADVERSARIAL_AUDIT_2026-08-13.md`.
