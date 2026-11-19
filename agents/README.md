# Agent setup

Config for the coding agents I use (Claude Code, Cursor, OpenCode): a pre-PR review loop, writing-style rules, and a few skills. The same files are linked into every machine. What a machine learns from its own reviews stays on that machine.

## What's here

| Folder | What it is | Linked to |
| --- | --- | --- |
| `review/` | The review engine: the `review` CLI, reviewer prompts, always-on rules, templates. See `review/README.md`. | `~/.agents/review` |
| `skills/pre-pr` | Runs a review round before a push: checks, parallel reviewers, a verifier | `~/.agents/skills/pre-pr` |
| `skills/review-retro` | Measures the reviewers against what happened to PRs, then tunes this machine's local files | `~/.agents/skills/review-retro` |
| `skills/unslop` | Writing rules applied to all prose an agent writes | `~/.agents/skills/unslop` |
| `skills/show-me` | `/show-me`: explain the current topic with a diagram or sketch | `~/.agents/skills/show-me` |
| `claude/hooks/` | Claude Code hook that loads the unslop rules | `~/.claude/hooks/` |
| `cursor/hooks/` | Cursor sessionStart hooks that load the unslop and review rules | `~/.cursor/hooks/` |
| `opencode/` | OpenCode review-gate plugin and `AGENTS.md` | `~/.config/opencode/` |

Claude Code also gets `~/.claude/skills/<name>` links. Cursor and OpenCode read `~/.agents/skills` directly.

## Setting up a machine

```sh
git clone https://github.com/josemlrod/.files.git ~/.files
~/.files/agents/install.py --dry-run    # see what it will change
~/.files/agents/install.py
```

It sets up whichever of the three agents are installed (or pass `--agents claude,cursor`). Running it again changes nothing. It needs `python3` 3.9+ and `git`, plus `gh` for the PR harvest.

The installer links the files above. In config files that other tools share, it adds only its own entries: hooks in `~/.claude/settings.json` and `~/.cursor/hooks.json`, two `@` imports in `~/.claude/CLAUDE.md`, and `instructions` plus `permission.skill["show-me"] = "ask"` in `~/.config/opencode/opencode.jsonc`. Anything it replaces or edits is copied to `~/.agents-install-backup/<timestamp>/` first. If `opencode.jsonc` has comments, it prints the lines to add by hand instead of rewriting the file. `--uninstall` removes what it added. With `--agents`, it keeps the shared `~/.agents` links while another installed agent still uses them.

After an install that changes OpenCode, run `opencode service restart`.

## What stays on each machine

`~/knowledge/review/` is never in this repo:

- `local/rules.md`: agent rules for this machine, such as a company's PR-title format. The installer creates it empty.
- `local/reviewers/`, `local/pre-pr.md`: reviewer and flow tuning from retros.
- `<repo>/REVIEW.md`, `<repo>/verify.md`: per-repo review rules and checks.
- `log.jsonl`, `state/`, `prs/`, `retros/`: review history.

The retro writes only there, so tuning from work repos never reaches personal machines. When a local change proves itself across two retros and isn't specific to a repo or company, the retro report lists it as a candidate. Copy it into this folder and commit it by hand.

## Changing things

The live paths are symlinks into this repo, so editing `~/.agents/review/...` or `~/.agents/skills/...` edits the repo. Commit and push from `~/.files`.
