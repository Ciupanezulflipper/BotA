# BotA Repair Error Log Addendum — 2026-08-02

This addendum records workflow and implementation defects discovered while repairing the failed August production validation. It supplements `audits/ERROR_LOG.md` and must be considered before later repository or phone work.

## E036 — Historical readiness was treated as current production truth

The July 26 control-plane closure remained prominent after the August 1 production validation had failed.

Effect:

- new work could incorrectly restart from `READY / AWAITING OPEN MARKET`;
- the August control-plane regressions, disabled automatic recovery, and repository/runtime divergence could be missed.

Prevention:

- later verified incident evidence supersedes older readiness snapshots;
- update the root handoff and issue #9 after every material validation failure or repair closure;
- distinguish historical PASS evidence from current production readiness.

## E037 — A preservation PR expanded far beyond its declared scope

PR #24 was described as a three-file preservation branch but later contained seven commits and thirty-two changed files from an old divergent base.

Effect:

- the PR body no longer described the branch;
- stale documentation, incident content, runtime code, tests, and experimental recovery code became mixed;
- the branch was nonmergeable and unsafe to deploy.

Prevention:

- compare declared files with actual changed files before every new commit;
- stop using a preservation PR once its purpose changes;
- create one fresh current-main branch per defect class;
- close contaminated branches as historical evidence rather than repairing them in place.

## E038 — Advancing main made an otherwise green branch nonmergeable

The first D1 repair branch passed analyzers, but documentation repair advanced `main` and left the D1 branch nonmergeable.

Prevention:

- never force-update or merge histories to rescue a stale repair branch;
- recreate the same complete files on a fresh branch from current `main`;
- close the stale PR as superseded and retain it only as analysis evidence.

## E039 — Combined Python and shell scope obscured an analyzer defect

The first status repair combined formatter logic, shell delivery, transport diagnostics, and broad tests in one PR. Sonar reported a reliability failure without exposing the issue location through the available connector.

Effect:

- repeated heuristic changes created noise;
- it became difficult to determine whether Python or shell code caused the red gate.

Prevention:

- split independent language/runtime concerns into separate PRs;
- validate the Python formatter independently from the shell sender;
- do not merge while any quality gate is red or opaque;
- supersede the combined branch instead of accumulating diagnostic commits indefinitely.

## E040 — A skip test checked its marker after deleting the fixture

Two autostatus tests checked whether the formatter marker existed only after `TemporaryDirectory` had removed the entire test tree.

Effect:

- the tests would report `formatter not called` even if it had run;
- market-gate ordering could receive a false PASS.

Prevention:

- capture observable state before temporary fixtures are destroyed;
- test the negative path behaviorally, not only through source-string ordering;
- treat test correctness as production reliability work.

## E041 — Fixed temporary files allowed overlapping status runs to collide

The original status sender used shared `tmp/as.out` and `tmp/as.err` paths.

Effect:

- concurrent cron or manual runs could overwrite each other's formatter output and errors;
- one invocation could send another invocation's message.

Prevention:

- use one unique `mktemp` directory per invocation;
- remove only known files, then remove the generated directory;
- avoid recursive cleanup when the exact temporary files are known.

## E042 — Telegram transport diagnostics were discarded

Status and heartbeat paths used silent curl behavior or redirected output to `/dev/null`, reducing failures to generic messages.

Effect:

- DNS, timeout, HTTP, Telegram rejection, and configuration failures could not be distinguished;
- repeated retries could occur without actionable evidence.

Prevention:

- bound connect and total timeout;
- retain transport exit status, HTTP status, stderr, and a bounded response body;
- persist a bounded last-error value;
- rate-limit retries with monotonic state;
- never log secrets or arbitrary unbounded response data.

## E043 — Non-standard numeric JSON fixtures distorted quality analysis

A regression fixture serialized positive infinity, which Python permits as `Infinity` but standard JSON does not.

Effect:

- quality tooling reported reliability concerns unrelated to the intended production boundary;
- the fixture did not represent a standards-compliant cache document.

Prevention:

- use valid JSON fixtures such as an invalid numeric string when testing rejection;
- test `NaN` and infinity directly at numeric conversion boundaries, not by serializing them into JSON.

## E044 — A transport helper accepted an arbitrary destination URL

The first heartbeat controller accepted an API URL argument even though production should contact only Telegram.

Effect:

- configuration or future callers could redirect heartbeat payloads to another host;
- static security analysis could reasonably classify the boundary as server-side request forgery risk.

Prevention:

- pin the transport to the Telegram API host inside the controller;
- accept only the bot token, chat ID, and message;
- quote the token as a path component;
- never log the token or full endpoint.

## E045 — Monotonic rollback alone is not a complete reboot detector

A new boot may eventually reach an uptime greater than the prior boot's saved monotonic timestamp. At that point, comparison alone cannot prove a reboot.

Prevention:

- persist the kernel boot ID when readable;
- reset delivery cadence when the boot ID changes;
- use monotonic rollback only as a fallback when boot ID is unavailable;
- do not depend on `/proc/uptime` on this Android build.

## E046 — Broad rediscovery was requested after authoritative discovery had completed

The August 2 cache and data discovery already ended with:

```text
LOCAL_STATUS_DATA_DISCOVERY_COMPLETE=YES
RUNTIME_MUTATION_PERFORMED=NO
GIT_CHANGED=NO
```

Prevention:

- consume existing continuity, incident, error, issue, and repository evidence before asking for more terminal output;
- repeat only a narrow datum whose freshness materially changes the next action;
- never rerun broad process, cache, history, and log discovery as one package.

## Current anti-repeat sequence

1. Read `CURRENT_REPAIR_HANDOFF_2026-08-02.md`.
2. Read the August 1 incident and this addendum.
3. Confirm the branch starts from current `main`.
4. Limit the package to one defect class and one language/runtime boundary when practical.
5. Replace complete files only.
6. Use focused behavioral tests with no real provider or Telegram calls.
7. Resolve exact analyzer findings.
8. Merge only the final reviewed head.
9. Record closure before starting phone deployment.
