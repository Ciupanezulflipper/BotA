# Android/Termux Engineering Toolchain Baseline

Last verified: **2026-08-08**

This is the shared phone-level Android/Termux engineering baseline used across BotA, LifVio, and dividend-capture-scanner. It is stored in GitHub so future AI sessions can discover the environment without relying on chat history.

This is not a project dependency manifest. Installed tools are available on the phone, but project hooks, auto-formatting, and project-specific configuration remain opt-in.

## Host baseline

```text
Termux 0.118.3
Distribution source: F-Droid
Architecture: aarch64
Python: 3.14.6
Node: 26.4.0
npm: 11.19.0
Git: 2.55.0
Package health: PASS
```

Final checks:

```text
dpkg --audit -> clean
apt-get check -> clean
ffmpeg -> working
yazi -> working
```

## Installed and verified tools

| Upstream project | Command | Version | Purpose |
|---|---|---:|---|
| cli/cli | gh | 2.97.0 | GitHub CLI for PRs, issues, checks, releases, workflows, and repository operations. |
| tmux/tmux | tmux | 3.7b | Persistent terminal workspace and multiple shells. Does not override Android process killing. |
| jesseduffield/lazygit | lazygit | 0.64.0 | Phone-friendly Git UI for status, branches, commits, diffs, staging, and conflicts. |
| BurntSushi/ripgrep | rg | 15.2.0 | Fast recursive repository text/code search. |
| junegunn/fzf | fzf | 0.74 | Fuzzy selection for files, history, branches, and command output. |
| sharkdp/fd | fd | 10.4.2 | Fast file discovery. |
| sharkdp/bat | bat | 0.26.1 | Syntax-highlighted file viewing. |
| ajeetdsouza/zoxide | zoxide | 0.10.0 | Fast learned directory navigation. |
| jqlang/jq | jq | 1.8.2 | JSON inspection and transformation. |
| mikefarah/yq | yq | 4.53.3 | YAML/JSON inspection and transformation. |
| mvdan/sh | shfmt | Termux package 3.13.1 | Shell formatting. Binary reports `(devel)`. |
| koalaman/shellcheck | shellcheck | 0.11.0 | Shell static analysis. |
| rhysd/actionlint | actionlint | 1.7.12 | GitHub Actions workflow validation. |
| astral-sh/ruff | ruff | 0.16.2 | Fast Python linting and formatting checks. |
| oxc-project/oxc | oxlint | 1.77.0 | Fast JavaScript/TypeScript linting. |
| oxc-project/oxc | oxfmt | binary 0.62.0; Termux package 1.77.0 | JavaScript/TypeScript formatting. |
| sxyazi/yazi | yazi / ya | 26.5.6 | Terminal file manager and companion CLI. |
| astral-sh/uv | uv | 0.12.3 | Python tool/environment manager. |
| pre-commit/pre-commit | pre-commit | 4.6.1 | Local hook framework. Installed; no repo hooks enabled automatically. |
| Yelp/detect-secrets | detect-secrets | 1.5.0 | Credential-pattern scanning. Installed; no project baseline enabled automatically. |
| pypa/pip-audit | pip-audit | 2.10.1 | Python dependency vulnerability auditing. |
| yamadashy/repomix | repomix | 1.18.0 | Packs selected repository context for AI handoff/review. |
| github/spec-kit | specify | 0.16.1 | Spec-driven development workflow tooling. |
| tt-a1i/archify | Claude skill | installed, doctor PASS | Architecture-oriented repository context and mapping. |
| upstash/context7 | ctx7 setup | CLI 0.5.7 at setup | Current-library documentation workflow for AI coding sessions. |

## Spec Kit state

- specify-cli 0.16.1 is verified on Python 3.14.6 / Android / aarch64.
- The official Git extension was added.
- Only a disposable test project was initialized during evaluation.
- BotA, LifVio, and dividend-capture-scanner were not initialized or changed by Spec Kit.

## Deliberate non-installs

- Knip: project-local/on-demand only.
- dependency-cruiser: project-local/on-demand only.
- ast-grep: deferred on Android.
- zizmor: deferred on Android.
- OSV-Scanner: deferred on Android.
- Gitleaks 8.30.1: rejected for this baseline because of an upstream regression found during audit.
- Codesurf: rejected as insufficiently proven.
- A second Git TUI: rejected as duplication; LazyGit is the selected Git TUI.
- Docker/proot-heavy development wrappers: rejected for the phone workflow.
- Additional generic AI-agent wrappers: deferred/rejected unless they add a clearly missing capability.

## Installation notes

Yazi introduced a newer FFmpeg/native dependency set while older Termux packages were still present. A full Termux consistency upgrade was completed; FFmpeg and Yazi then passed.

The same upgrade moved system Python from 3.13 to 3.14.6. Existing uv-managed environments for pre-commit, detect-secrets, and specify-cli were rebuilt against Python 3.14.6 and verified successfully.

## Operating rules

1. Prefer official Termux packages when available.
2. This phone uses the F-Droid Termux build; Termux add-ons should use the matching distribution/signature source.
3. Do not assume tmux prevents Android from terminating processes.
4. Avoid partial native-library upgrades; keep the Termux package set consistent.
5. No project hooks, auto-fixers, baselines, or repo mutations were activated as part of this installation.
6. Before installing another global tool, check this file and justify the incremental value over the existing stack.
7. After a future major Python/Node/Termux upgrade, revalidate the CLI inventory.
