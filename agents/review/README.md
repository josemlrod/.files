# Local pre-PR review

A diagram and plain-language overview lives outside this repo, on the work machine only: `~/knowledge/diagrams/local-review/architecture/show-me-local-review-architecture.html`.

A personal version of the review process the Claude Code team describes in "How the Claude Code team does code review" (Addy Osmani, 2026). It runs in Claude Code, Cursor, and OpenCode, in every repo on the machine, and adds nothing to any project repo.

The engine (this folder and the `pre-pr` and `review-retro` skills) lives in the `.files` repo under `agents/` and is linked into `~/.agents/` by `agents/install.py`. It is the same on every machine. Review data, per-repo rules, and everything a retro tunes stay in `~/knowledge/review/` on the machine that produced them.

## What happens

1. While an agent edits, a hook runs the repo's formatter on each edited file (from the Format section of `verify.md`).
2. Before saying a task is done, the agent runs the repo's checks and shows the commands and results (`RULES.md`).
3. Before pushing, the agent runs the `pre-pr` skill:
   - It runs the checks again and keeps the output.
   - It computes a risk tier from the diff size and the high-risk paths in `REVIEW.md`.
   - It starts 2 to 6 reviewers in parallel, each with a fresh context: bugs (diff, system, intent), security, and repo rules.
   - A verifier tries to disprove each finding and keeps only the ones it confirms.
   - Findings in code the branch didn't change are labeled pre-existing and never block.
   - It records the round and drafts the PR's Testing, Risk, and How to revert sections.
4. Git's pre-push hook blocks a push until a round passes for the exact tree being pushed. The installer makes a read-only `~/.agents/git-hooks` folder holding a read-only stub, `_run`, that runs `git-hooks/_dispatch`, and one link to the stub per git hook name. Git never rewrites the stub, so it stays read-only across pulls of `.files`. The stub also fixes the review data folder, so a push run with a different `HOME` or `REVIEW_DATA_DIR` still checks the real review state. It runs the dispatcher with `/bin/bash -p` and clears `BASH_ENV`, `ENV`, `SHELLOPTS` and `BASHOPTS`, so a calling script's shell settings can't break or skip it. The gate keeps agents that follow `RULES.md` from pushing unreviewed code by accident. It is not a sandbox: an agent that sets out to get around it, for example by editing files or `PATH`, still can. Agents' shells point git's `core.hooksPath` at it through `GIT_CONFIG_*` environment variables, so git runs the check on pushes from those shells whatever the command looks like (`gh pr create` pushes through git too). The dispatcher then runs the repo's own hooks, such as husky's. Pushes of tags, deletes, other non-branch refs, and branches with nothing new compared with the default branch are not checked. A pre-tool hook is a best-effort check for commands that would skip git's hook (`--no-verify`, a `core.hooksPath` override, changed `GIT_CONFIG_*` variables). It reads command text, so it can miss an unusual spelling and can block a command that only mentions those options. Hook installers such as lefthook or `pre-commit install` see `~/.agents/git-hooks` as the repo's hooks folder; it is read-only so they fail visibly instead of replacing the gate. Run them with the three `GIT_CONFIG_*` variables unset. A round passes when the checks pass and no Important finding is open. A new commit needs a new round. Rounds after the first only review what changed. After 3 failed rounds in a row the agent stops and asks you to rethink the approach.
5. Once a day, starting from the first `pre-pr` round, `review harvest` runs in the background. It records what happened on GitHub to every reviewed branch's PR: teammates' comments, approvals, wait times, CI failures, and reverts. These are read-only `gh` calls. Nits still open at merge are recorded as `open-at-merge`, and a revert of a reviewed PR becomes an eval case.
6. After 10 rounds, `pre-pr` says a retro is due. After the first retro, it also waits until 14 days have passed since the last one. The `review-retro` skill measures noise and misses from all of this data, writes a report, proposes changes, and applies the ones you approve. It writes only to `~/knowledge/review/`: per-repo `REVIEW.md` and `verify.md`, or the `local/` overlay. It never edits the engine. When a local change has held up for two retros and isn't specific to a repo or company, the report lists it as a candidate to copy into `.files` by hand.

## Files

Shared engine, from `.files/agents/`:

| Path | What it is |
|---|---|
| `~/.agents/review/RULES.md` | Always-on rules loaded into every agent session |
| `~/.agents/review/bin/review` | CLI for state, the gate, the formatter, and hook adapters (Python stdlib) |
| `~/.agents/review/reviewers/*.md` | Reviewer and verifier prompts |
| `~/.agents/review/templates/` | Starting `REVIEW.md` and `verify.md` for a new repo |
| `~/.agents/skills/pre-pr/SKILL.md` | The review flow (linked into `~/.claude/skills`) |
| `~/.agents/skills/review-retro/SKILL.md` | The retro (linked into `~/.claude/skills`) |

This machine only, in `~/knowledge/review/`:

| Path | What it is |
|---|---|
| `~/knowledge/review/local/rules.md` | This machine's agent rules, loaded after `RULES.md`. Company rules go here. |
| `~/knowledge/review/local/reviewers/<name>.md` | Additions to a reviewer prompt (`_shared.md` for all of them). They win where they conflict. |
| `~/knowledge/review/local/pre-pr.md` | Changes to the `pre-pr` flow, such as tiers or reviewer sets |
| `~/knowledge/review/<repo>/REVIEW.md` | Per-repo rules: failures, high-risk and ignored paths, conventions |
| `~/knowledge/review/<repo>/verify.md` | Per-repo formatter and checks |
| `~/knowledge/review/state/<repo>/<branch>.json` | Rounds and findings for a branch |
| `~/knowledge/review/log.jsonl` | Every round, finding, verifier rejection, outcome, skip, PR result, and revert |
| `~/knowledge/review/prs/<repo>/<n>.json` | Harvested PR data: comments by teammates and bots, approvals, CI, reverts |
| `~/knowledge/review/evals/cases.jsonl` | Reviewed PRs that were later reverted; `results.jsonl` holds replay scores |
| `~/knowledge/review/retros/<date>.md` | Retro reports |
| `~/knowledge/review/CHANGES.md` | Tuning changes, with prompt versions before and after |
| `~/knowledge/review/proposals.md` | Changes that belong in a repo or the team's process, for later |

`<repo>` is the name from the `origin` remote, so worktrees and fresh clones share one config.

## How each agent is wired

| | Rules | Git hooks folder | Hook-skip check | Formatter |
|---|---|---|---|---|
| Claude Code | `@~/.agents/review/RULES.md` and `@~/knowledge/review/local/rules.md` in `~/.claude/CLAUDE.md` | `env` in `~/.claude/settings.json` | `PreToolUse` on `Bash` | `PostToolUse` on `Edit\|Write\|MultiEdit` |
| Cursor | `sessionStart` hook `~/.cursor/hooks/review-rules.sh` (reads both rule files) | `~/.zshenv` block, when `CURSOR_AGENT` is set | `beforeShellExecution` in `~/.cursor/hooks.json` | `afterFileEdit` |
| OpenCode | `instructions` in `~/.config/opencode/opencode.jsonc` | `~/.zshenv` block, when `OPENCODE_SESSION_ID` is set (its bash tool sets it; its terminal panel doesn't) | `~/.config/opencode/plugins/review-gate.js` (`execute.before`) | same plugin (`execute.after`) |

Cursor and OpenCode get the git variables only when they run commands with zsh, which reads `~/.zshenv` for every shell.

`agents/install.py` in `.files` sets all of this up and can be run again safely.

The gate only affects agents. Your own terminal never gets the git variables, and the repos' git hooks and CI are untouched. OpenCode 2.x loads plugins in a background service. After you change the plugin, run `opencode service restart`.

## Commands

```bash
review status                                   # rounds and open findings for this branch
review outcome fixed F3                         # finding is fixed
review outcome rejected F3 --reason "..."       # also: intentional, ignored
review skip --reason "..."                      # pass the gate once for the current commit
review harvest                                  # fetch PR outcomes now (also runs daily in the background)
review stats --days 30                          # the numbers the retro uses
review version                                  # hash of the current reviewer prompts
touch ~/knowledge/review/GATE_OFF               # turn the gate off everywhere; rm to turn it back on
```

`review` is `~/.agents/review/bin/review`.

## Adding a repo

Copy the two templates to `~/knowledge/review/<repo>/` and fill them in, or ask an agent to do it from the repo's `CLAUDE.md`, CI workflows, CODEOWNERS, and revert history. Without them, `pre-pr` still runs and uses the repo's obvious commands.

## Removing it

Run `~/.files/agents/install.py --uninstall`. It removes the links and hook entries it added and leaves `~/knowledge/review/` alone. Anything it replaced or edited is copied first to `~/.agents-install-backup/<timestamp>/`.
