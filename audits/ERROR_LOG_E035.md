# BotA Runtime Error Log Addendum

## E035 — Placeholder commits were created directly on main

During GitHub-only preparation for PR #18, three temporary placeholder files were
accidentally created directly on `main` while attempting to establish a branch.
Each placeholder contained only `x` and was deleted immediately. No placeholder
file remains in the repository, but the create/delete commits remain in history.

Effect:

- the no-direct-push-to-main rule was violated;
- repository history contains avoidable create/delete commits;
- no phone, service, process, strategy, provider, Telegram, Supabase, or runtime
  state was changed.

Prevention:

- create and verify the target branch with `create_branch` before any file write;
- confirm the branch exists before calling `create_file` or `update_file`;
- never use a placeholder file to probe branch creation;
- stop after the first branch-not-found response and load the exact branch action;
- perform all future repository mutations on an explicitly verified non-main
  branch, followed by a pull request and exact-head merge.

This addendum must be displayed together with `audits/ERROR_LOG.md` before the
next phone mutation. It may be folded into the canonical error log in a later
normal documentation maintenance change without blocking the approved runtime
reconciliation.
