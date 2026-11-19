---
name: pre-pr
description: Verify and review the current branch before pushing or opening a pull request. Runs the repo's checks and shows their output, sizes the review by risk, runs fresh-context reviewers in parallel, filters their findings through a verifier, records the round, and drafts the PR's Testing, Risk and How to revert sections. Use before any git push or gh pr create (git's pre-push hook blocks pushes until this passes), when the user says "review my changes", "pre-pr", "is this ready", or after finishing a coding task in a git repo.
---

# Pre-PR review

This runs the local version of a layered review: checks that prove the change works, then reviewers with fresh context, then a verifier that drops false positives. Git's pre-push hook blocks a push until a round passes for the exact code being pushed.

The CLI is `~/.agents/review/bin/review`. Run it from inside the repo. It stores state in `~/knowledge/review/` and never writes to the repo.

This file and the reviewer prompts are the same on every machine. Each machine can add to them in `~/knowledge/review/local/`, which the retro writes to. Where the two conflict, the local file wins.

## 1. Start the round

```bash
~/.agents/review/bin/review info
```

It prints JSON. Keep it: you pass parts of it to the reviewers. If `local_pre_pr` is set, read that file now and apply it on top of the steps below. `round_dir` is a new folder for this round's files; it starts with `findings.json` and `rejected.json` set to `[]`. Read these fields:

- `rethink: true` means 3 rounds in a row failed. Stop. Tell the user, list the open findings, and suggest a different approach. Do not run another round unless the user says to.
- `mode`:
  - `full`: first review of this branch.
  - `incremental`: review only `files_to_review` and only what changed since `incremental_from_tree`.
  - `already-reviewed`: nothing changed since the last round. If the last round passed, say so and stop. If it failed only on checks, or on findings that step 2 now resolves, rerun the checks (step 3) and go to step 6 with no reviewers. Say in the report that no reviewers ran. A finding raised in this same code can't be fixed without changing it: `record` reopens any Important finding marked fixed whose round reviewed the same tree.
- `tier`: `low`, `medium`, or `high`, computed from the size and the high-risk paths in `review_md`. Raise it in step 4 if needed. Never lower it below the tier the step 4 rules give for the files under review.
- `open_findings`: findings from earlier rounds that are still open.
- `review_md`, `verify_md`: the repo's local rules and checks. If they are null, say so in the report and use the repo's obvious lint, type, and test commands.

## 2. Settle earlier findings

For each finding in `open_findings`, read the code now at that location.

- If it is fixed, run `~/.agents/review/bin/review outcome fixed F3` (several IDs are allowed).
- If the user said in this conversation that it is intended or not worth fixing, run `~/.agents/review/bin/review outcome intentional F3 --reason "<their words>"` or `ignored`.
- Never mark an `important` finding `rejected`, `intentional`, or `ignored` on your own judgment. Show it to the user and ask. A nit you can resolve yourself with a specific reason.

Pass the remaining open findings to the reviewers as `known_findings` so nobody reports them again.

## 3. Run the checks and keep the proof

Read `verify_md`. Run every check whose "When" matches the changed files, scoped to those files when the command allows it. For UI or behavior changes, follow its "Manual and UI checks" section. Never run anything its "Not runnable locally" section or the repo docs say touches production.

For each check, keep the command, the exit code, and the last lines of output. Build this JSON and save it to `<round_dir>/checks.json`:

```json
{"ok": true, "results": [
  {"name": "types", "command": "yarn tsc --noEmit", "ok": true, "summary": "0 errors"},
  {"name": "unit", "command": "yarn jest src/foo", "ok": false, "summary": "1 failed: renders total"},
  {"name": "e2e", "command": null, "ok": null, "summary": "not run: needs staging credentials"}
]}
```

`ok` at the top is true only when every check that ran passed. A check you could not run gets `"ok": null` and a reason. It does not fail the round, but it must appear in the report and in the PR's Testing section. Never claim a check passed if you did not run it.

## 4. Pick the reviewers

Raise the tier to `high` if the change touches auth, payments or billing, data deletion or migration, CI, release config, or installers, even when no glob caught it.

| Tier | Reviewers |
|---|---|
| low | `bugs` (focus `diff`), `repo-rules` |
| medium | `bugs` (focus `diff`), `bugs` (focus `system`), `bugs` (focus `intent`), `security`, `repo-rules` |
| high | the medium set plus a second `bugs` (focus `diff`) |

On an `incremental` round, pick the reviewers from what changed since `incremental_from_tree`, not from the branch tier:

- Only comments, docs, or test names changed, or the round only replays a rebase onto the base branch with no conflict edits: the low set.
- Otherwise, the tier computed for those changed files alone, with the raise rules above. If any changed file is on a high-risk path, use the branch tier.

Say which rule you used in the round's first line.

Get `intent` from the PR body (`gh pr view --json title,body`), the task the user gave you, or `git log --format=%s%n%b <merge_base>..HEAD`.

## 5. Run the reviewers in parallel, with fresh context

Start one subagent per reviewer, all in the same turn so they run at the same time. Use your agent's subagent tool: `Agent` (general-purpose) in Claude Code, `Task` in Cursor, `task` in OpenCode. Each prompt is:

```
Read <reviewers_dir>/<name>.md and follow it. Then, if they exist, read
<local_reviewers_dir>/_shared.md and <local_reviewers_dir>/<name>.md: they are
this machine's additions and win where they conflict. Do not edit any files.
Inputs:
  root: <root>
  merge_base: <merge_base>
  files_to_review: <files_to_review>
  incremental_from_tree: <value or null>
  intent: <intent>
  review_md: <review_md or null>
  focus: <diff|system|intent, bugs reviewer only>
  known_findings: <open findings as JSON>
```

Do not add your own view of the change to the prompt. A reviewer that knows what you think tends to agree with it.

If your agent has no subagent tool, run each reviewer file yourself in sequence, and write "inline review, not fresh context" in the report.

Merge the arrays the reviewers return and tag each item with `"reviewer": "<name>[:<focus>]"`.

## 6. Verify the findings

If there are candidates, start one more fresh subagent with `<reviewers_dir>/verify-findings.md` (plus the local `_shared.md` and `verify-findings.md` additions, as in step 5), the same `root`, `merge_base`, and `review_md`, and the merged array. Keep only what it confirms.

Save the candidates it rejected as a JSON array to `<round_dir>/rejected.json`: `{"reviewer": "...", "class": "...", "file": "...", "title": "...", "reason": "..."}`. Match each `rejected:` line to its candidate to fill in the reviewer, class, and file. These are the false positives the retro uses to tune the reviewers, so keep the verifier's reason.

Set the final severity:

- `in_diff: false` becomes `"severity": "pre-existing"`. It never blocks, so the author isn't held responsible for old bugs.
- Otherwise use the verifier's `important` or `nit`.

Save the confirmed findings, with their final severity, as a JSON array to `<round_dir>/findings.json`. Leave `findings.json` or `rejected.json` as `[]` when there is nothing to put in it.

## 7. Record the round

```bash
~/.agents/review/bin/review record --reviewers bugs:diff,bugs:system,security [--tier high]
```

It reads `findings.json`, `checks.json`, and `rejected.json` from the round's `round_dir`.

`--reviewers` lists the reviewers that ran, as `name` or `name:focus`. `--tier` is only needed when you raised it. The output says `pass` or `fail`. A round passes when the checks passed and no `important` finding is open. Nits never block.

## 8. Report

Start with one line: `Round N · tier T · mode M · X important, Y nits, Z pre-existing`, or `Round N · tier T · no issues found`. Then:

1. The checks: command, result, and anything not run with the reason.
2. The findings, important first, then nits, then pre-existing. Give each one as `F# path:line [class] title`, the failure scenario in one sentence, and the fix.
3. How many candidates the verifier rejected.
4. If `info` returned `"retro_due": true`, end with one line: "Enough review data has built up for a retro: run the review-retro skill."

## 9. After the report

**If the round failed**, and fixing is part of the task you were given, fix every `important` finding. Fix the whole class of the bug, every place it appears, not just the reported line. Then run this skill again: the next round reviews only what changed. Leave nits unless the fix is trivial and certain. If 3 rounds have failed, stop and talk to the user about the approach instead.

**If the round passed**, draft these sections for the PR description. If the repo has a pull request template (`.github/pull_request_template.md` or `.github/PULL_REQUEST_TEMPLATE.md`), fill its matching sections instead of adding new ones.

- **Testing**: each check with its command and result, the manual checks done, and what was not run and why.
- **Risk**: the tier and why. For `high`, write "Needs a human review of:" and list the high-risk files and what a reviewer should look at in each.
- **How to revert**: usually "Revert the merge commit." Add any steps a revert alone won't undo, such as migrations, backfills, feature flags, published packages, or external config.

## Rules

- When the user dismisses a finding at any point, record it: `~/.agents/review/bin/review outcome <rejected|intentional|ignored> F# --reason "<why>"`. The log of what happened to each finding is how the reviewers get tuned.
- Only run `~/.agents/review/bin/review skip --reason "<the user's words>"` when the user explicitly tells you to skip review for this push. It passes the gate once, for the current commit only.
- Run `~/.agents/review/bin/review status` to see the branch's rounds and open findings.
