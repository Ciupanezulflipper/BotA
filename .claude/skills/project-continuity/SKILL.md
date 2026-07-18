---
name: project-continuity
description: Create an exact project checkpoint from repository, runtime, deployment, database, and active-conversation evidence. Use for status reviews, new-chat handoffs, continuity logs, or package closure.
user-invocable: true
---

# Project Continuity

Create a compact checkpoint that another session can continue without repeating proven work or inventing state. Work read-only unless the user explicitly asks to update a file or repository.

## Evidence rules

- Current repository and runtime evidence govern current state.
- Historical notes are supporting evidence, not automatic truth.
- Use exact dates, branch names, SHAs, deployment IDs, and project IDs.
- Mark important claims as `proven`, `inferred`, or `not proven`.
- A check that did not execute is never PASS.
- Do not request evidence already proven for the same unchanged head and environment.
- Do not include credentials or raw environment values.
- Audit recent history before recommending paid resources or replacement infrastructure.

## Detect authority

### LifVio

Read in this order:

1. `CLAUDE.md`
2. `docs/CURRENT_STATE.md`
3. exact GitHub, Vercel, Supabase, and repository evidence
4. active approved task
5. task-specific records
6. `docs/CLAUDE_CHAT_HANDOFF.md` only when required

Use the bounded-delta method in `CLAUDE.md`; do not read the complete historical handoff by default.

### BotA

Read in this order:

1. live repository and Termux runtime evidence
2. `BOTLOG.md`
3. active branch or PR evidence
4. exact logs and proof artifacts
5. older reports

Re-prove cron, watcher, provider freshness, decision journaling, and delivery state before accepting an old status entry.

### Other projects

Discover the closest equivalents of durable rules, semantic state, exact repository state, runtime state, active approval, blockers, and boundaries. Report a missing canonical state source as a risk instead of inventing one.

## Collect the checkpoint

Repository:

- repository and remote;
- default and active branch;
- worktree state;
- local and remote head;
- current main;
- divergence;
- PR number, base, head, draft state, mergeability, and changed files.

Validation:

- checks that executed and their exact result;
- checks unavailable and why;
- outstanding checks;
- bounded exceptions and expiry conditions.

Runtime and deployment when relevant:

- Production URL;
- deployment ID and exact commit;
- state and aliases;
- route behavior;
- runtime errors and logs;
- rollback state.

Database and services when relevant:

- exact project identity and health;
- migration and schema state;
- key row-count baselines;
- gates and permissions;
- whether any mutation occurred;
- whether the schema is active or dormant.

Do not mutate a system merely to improve a continuity record.

## Output format

```text
PROJECT CHECKPOINT — [exact date/time]

Project:
Repository:
Production/runtime:

Canonical authority:
- durable rules:
- semantic state:
- active approval:

Repository state:
- active branch:
- exact head:
- current main:
- PR:
- worktree:

Completed and proven:
- ...

Implemented but not released:
- ...

Production/runtime state:
- ...

Database/service state:
- ...

Validation:
- PASS:
- unavailable:
- outstanding:
- bounded exceptions:

Known limitations and blockers:
- ...

Protected boundaries not authorized:
- ...

Next safe package:
- purpose:
- permitted scope:
- stop conditions:
- approval required:
```

Keep it short enough for a new chat, but include every value needed to prevent a wrong branch, wrong environment, repeated test, or accidental boundary crossing.

## Writing canonical state

Only write when explicitly requested.

Before writing:

1. Read the project's durable rules.
2. Identify the canonical state file and update triggers.
3. Inspect the bounded Git delta since the prior semantic checkpoint.
4. Verify connected runtime evidence when available.
5. Preserve historical dates.
6. Use complete-file replacement for the user's Termux workflow.
7. Re-fetch the remote before committing and stop if it moved.

For LifVio, update `docs/CURRENT_STATE.md` only for triggers defined in `CLAUDE.md`.

For BotA, update `BOTLOG.md` only with evidence from the active session. Do not rewrite strategy history to fit a theory.

## Final quality check

Confirm:

- every SHA and branch is exact;
- Production commit was checked independently from main;
- database identity is exact;
- no unavailable check is labeled PASS;
- the next package is the smallest safe step;
- approval boundaries are explicit;
- the checkpoint stands alone without the previous chat.

## Invocation

`/project-continuity $ARGUMENTS`

Without arguments, summarize the active project read-only and identify the next safe package. Do not start it automatically.
