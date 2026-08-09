# BotA AI Start Here

Last updated: **2026-08-09 UTC**

Read this before proposing BotA commands, code, service, strategy, Telegram, provider, Supabase, replay, deployment, or Android/Termux changes.

## Current authoritative truth

```text
CHECKPOINT_BASE_MAIN=163eae4ee7a0d651ed0ad3516dba7eaef4c09cbe
PHONE_RUNTIME_SOURCE_BASELINE=5cbfbf11fd98d9a40b1d5ea28995f584ec9da080
PHONE_LOCAL_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_LOCAL_HEAD=4339543551aae2e2bcbf727aefe96e3eb103b665
PHONE_WORKTREE_DIRTY=YES

PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
TELEGRAM_ENABLED=1
DRY_RUN_MODE=0

PACKAGE_1_CLOCK_SESSION=PASS
PACKAGE_2_CONTROL_PLANE_RECOVERY=PASS
PACKAGE_2_FINALIZER_DEPLOY=PASS
PR87_PR88_PHONE_DEPLOY=PASS
REQUESTS_RUNTIME_DEPENDENCY=PASS_2.34.2
NATURAL_SHADOW_CYCLE=PASS
PRE_MARKET_PRODUCTION_INTEGRITY=PASS
PRE_MARKET_FAILURE_COUNT=0

CURRENT_MANAGER_COUNT=1
CURRENT_REQUIRED_SERVICES_OWNED=7/7
CURRENT_REQUIRED_SERVICES_RUNNING=7/7
CURRENT_ORPHANED_RUNSV=0
CURRENT_DUPLICATE_SERVICE_ROWS=0
WATCHDOG_SINGLETON=PASS
WATCHDOG_LOCK_SINGLETON=PASS
BOOT_PERSISTENCE=PASS
CRON_OWNERSHIP=PASS
RUNTIME_PARITY=PASS
PRODUCTION_CONFIG=PASS
PROFITLAB=PASS
TRUSTED_CLOCK=PASS

PR89_GUARDIAN=NOT_DEPLOYABLE_YET
OPEN_MARKET_THREE_PAIR_LIVE_PROOF=PENDING
MONDAY_READY=NO
```

`CHECKPOINT_BASE_MAIN` is the GitHub main commit used as the documentation base. The documentation merge containing this file advances `main`; GitHub issue #9 carries the live current-main SHA. The reviewed phone runtime source baseline remains `5cbfbf11...`.

## What has been proven on the phone

The control plane recovered from the observed orphan-supervisor failure class and currently satisfies the production ownership contract: one native manager, seven manager-owned required supervisors, seven running services, zero orphans, and zero duplicate service rows.

The native watchdog finalizer passed and left one watchdog process holding the watchdog lock. The managed Termux:Boot watchdog block is installed.

PR #87 and PR #88 production fixes were deployed from exact runtime source commit `5cbfbf11fd98d9a40b1d5ea28995f584ec9da080`. `requests==2.34.2` is installed and importable under Python 3.14.6. The installation did not change any previously installed Python distribution and did not worsen the pre-existing Termux `pip check` baseline.

A subsequent **natural** runit shadow cycle completed with `exit_code=0`, wrote an `OK` heartbeat, and logged `Shadow Manager done | 0 active signals`. It was not manually executed and no service was restarted for that proof.

The corrected pre-market integrity gate then returned all nine checks PASS with zero failure reasons:

```text
control_plane=PASS
watchdog_ownership=PASS
boot_persistence=PASS
cron_ownership=PASS
runtime_parity=PASS
production_config=PASS
profitlab=PASS
progress=PASS
trusted_clock=PASS
```

## Current strategy/runtime freeze

```text
POLICY_B_ENABLED=1
POLICY_B_SCORE_MIN=70
POLICY_B_ADX_MAX=30
NEWS_ON=0
DO_NOT_LOWER_THRESHOLDS=YES
DO_NOT_FORCE_SIGNAL_COUNT=YES
DO_NOT_FORCE_TELEGRAM_TEST_SIGNAL=YES
DO_NOT_BOOTSTRAP_PROFITLAB=YES
```

No readiness fix may manufacture signals by changing strategy thresholds, pair/timeframe scope, Telegram eligibility, or ProfitLab semantics.

## Current blocker: PR #89

PR #89 (`fix/watchdog-persistence-guardian-20260809`) is the only infrastructure blocker before the open-market proof. Do **not** deploy it in its current state.

Current head:

```text
4f73a999634bc83c52defb0d31bfb72291ac83b9
```

Current review/CI state includes `DeepSource: Python = failure` and unresolved still-valid findings. Required fixes include:

- use active advisory `FLOCK` ownership rather than open-descriptor ownership;
- safely quote all rendered cron paths and reject CR/LF injection;
- keep controlled `WATCHDOG_GUARD=FAIL` / RC 4 behavior even if event logging fails;
- replace incomplete grep termination checks with AST-based validation and negative fixtures;
- validate the complete rendered cron and exactly one active `--ensure` guardian line;
- reject NaN/infinite timeout values;
- resolve remaining lint/test-quality findings.

PR #89 must be review-clean and exact-head CI-clean before phone deployment or watchdog fault injection.

## Mandatory operating model

```text
GitHub connector / GitHub PR -> code, review, CI, commits, documentation
Phone / Termux              -> runtime-only evidence and approved deployment
```

Never equate code-ready, merged, deployed, runtime-verified, pre-market-ready, and Monday-ready.

Never push directly to `main`. Work on the existing PR branch, run tests, inspect review threads, commit intentionally, push the PR branch, then re-check exact-head CI/review.

## Read first

1. `CONTINUITY_CURRENT.md` — current operational status and next action.
2. `audits/PRE_MARKET_READINESS_CHECKPOINT_2026-08-09.md` — latest phone proof and remaining blocker.
3. GitHub issue #9 — authoritative readiness tracker and live current-main SHA.
4. PR #89 — guardian implementation and unresolved review findings.
5. `ERRORS.md` and `audits/ERROR_LOG.md` — historical failure/prevention record.

## Exactly one next engineering action

Fix PR #89 on its existing branch, without touching production strategy or the phone runtime. Require exact-head CI/static/review PASS before any deployment instruction is generated.
