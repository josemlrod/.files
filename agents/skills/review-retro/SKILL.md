---
name: review-retro
description: Retrospective on the local pre-PR review system. Pulls what happened to reviewed PRs on GitHub (teammates' comments, CI failures, reverts), measures reviewer noise and misses from the review log, and proposes concrete changes to the per-repo REVIEW.md and verify.md, the reviewer prompts, and the agent rules. Applies only the changes the user approves, and only to local files. Use when the user says "review retro", "tune the reviewers", "how is pre-pr doing", or when pre-pr reports that a retro is due.
---

# Review retro

The pre-PR review only gets better if someone looks at what it got wrong. This skill does that from data the system already logs. The goal is the one from the Claude Code team's post: less human effort per change, without more reverts, CI failures, or bugs found by teammates.

The CLI is `~/.agents/review/bin/review`. All data is in `~/knowledge/review/`. This skill changes files in `~/knowledge/review/` only. It never edits `~/.agents/review` or `~/.agents/skills`: those are links into the user's `.files` repo, shared by every machine, and the user changes them by hand. Tuning stays on the machine whose reviews produced it.

## 1. Collect

```bash
~/.agents/review/bin/review harvest          # read-only GitHub calls for every reviewed branch
~/.agents/review/bin/review stats --days N   # N = days since the last retro, or 30 for the first one
~/.agents/review/bin/review version          # current prompt version
```

The date of the last retro is the newest file in `~/knowledge/review/retros/`. Read that report and `~/knowledge/review/CHANGES.md` (if they exist) so you can compare against the last period and see which changes were made since.

If `stats` shows fewer than 5 rounds, say there is not enough data yet, show the numbers you have, and stop.

## 2. Measure

Build this table from `stats`. Add a column with the previous retro's values when there is one.

| Metric | From `stats` | What good looks like |
|---|---|---|
| Rounds, branches, PRs | `rounds.total`, `branches.total`, `prs.total` | |
| Cycles to pass (median, p95) | `branches.cycles_to_pass_*` | median 1 to 2 |
| Branches that hit the 3-round limit | `branches.hit_rethink` | none |
| Findings per round, by tier | `rounds.findings_per_round_by_tier` | low tier near 0 |
| Fixed, dismissed, open at merge | `findings.by_outcome` | most findings fixed |
| Noise rate (dismissed plus open at merge, over settled) | `findings.by_reviewer.*.noise_rate` | under 0.3 |
| Verifier rejections | `rounds.verifier_rejected` | |
| Skips of the gate | `skips` | rare, with reasons |
| Teammate comments per PR (median) | `prs.human_comments_median` | falling |
| Approvals per PR (median, p95) | `prs.approvals_*` | |
| Hours to first human review, to merge | `prs.hours_to_*` | |
| PRs with failed CI after a passing round | `prs.with_failed_checks` | none |
| Reverts found | `prs.reverts_found` | none |

## 3. Find what to change

Work through each source below. For every problem, write down the evidence: counts, PR links, finding titles, and the reasons people gave.

**Noise.** Look at `findings.by_class` and `findings.by_reviewer` entries with `noise_rate` of 0.5 or more and at least 3 findings, and at `examples.dismissed` and `examples.verifier_rejected`. Read the reasons. Typical fixes:
- A "Do not flag" line in that repo's `REVIEW.md`.
- A narrower instruction in the reviewer prompt that produced them.
- Dropping a reviewer from a tier where it rarely finds anything real.

**Misses from teammates.** For each PR in `prs.with_human_comments`, read its file and the comments where `who` is `human`. Ignore replies, approvals with no text, and pure questions. Sort each remaining comment into one of four groups:
- **A bug or broken convention the reviewers should have caught.** Check the branch's state file (`~/knowledge/review/state/<repo>/<branch>.json`) to see whether a finding already covered it.
- **Product, design, or "should we build this".** These are for humans. Leave them.
- **Style or taste.** Consider writing them down as a convention if the same one comes up twice.
- **Context the reviewer could not have had.** Consider adding it to `REVIEW.md`.

For the first group, propose the rule, convention, or check that would have caught it, and say which file it goes in.

**CI failures after a passing round.** For each PR in `prs.with_failed_checks`, find out why the local checks missed it: the check is missing from `verify.md`, it wasn't run because its "When" was too narrow, or it can't run locally. Propose the `verify.md` change, or a line under "Not runnable locally".

**Reverts.** For each entry in `prs.reverts_found`, read the PR and its revert to learn what broke. Propose a "Known bug-prone areas" line for that repo's `REVIEW.md`. The case is already in `~/knowledge/review/evals/cases.jsonl`, and step 5 can replay it.

**Recurring real bugs.** Look at `examples.recurring_fixed_classes` and classes in `findings.by_class` with many fixed findings. A bug class that keeps getting written and fixed should be stopped where it is written. Propose one of these:
- A line in `~/knowledge/review/local/rules.md` telling the coding agent to avoid it.
- A lint rule, as a repo-level proposal.
- A convention in `REVIEW.md`.

**Convergence and gate friction.** Look at `branches.hit_rethink`, at `rounds.by_mode` (are most later rounds incremental?), and at `skips` and their reasons. If skips cluster on one kind of change, such as docs only, propose a gate or tier change.

## 4. Write the report

Write `~/knowledge/review/retros/<YYYY-MM-DD>.md`:

1. One paragraph: the period, the data volume, and the 2 or 3 most important observations.
2. The metrics table from step 2.
3. Numbered proposals. Each one needs:
   - the target file, from the list below
   - the exact text to add, change, or remove
   - the evidence, with counts and links
   - the expected effect on the metrics

| Target | Applies where |
|---|---|
| `~/knowledge/review/<repo>/REVIEW.md` or `verify.md` | one repo |
| `~/knowledge/review/local/reviewers/<name>.md` | every repo on this machine, added to that reviewer's prompt (`_shared.md` for all reviewers) |
| `~/knowledge/review/local/rules.md` | every agent session on this machine |
| `~/knowledge/review/local/pre-pr.md` | tiers, reviewer sets, round rules on this machine |
| `~/knowledge/review/proposals.md` | changes that belong in a repo or the team's process, kept for when the user is ready to share |

Prefer the narrowest target that fixes the problem. A per-repo file affects one repo; a `local/` file affects every repo on this machine, including personal ones.

End the report with a short "Candidates for the shared engine" list: changes already in `local/` that have held up for at least two retros and say nothing about a specific repo or company. For each one, name the `.files` file it would go in (`agents/review/reviewers/<name>.md`, `agents/review/RULES.md`, or `agents/skills/pre-pr/SKILL.md`). The user decides whether to copy it there and commit. Leave the list out when it is empty.

Show the user the report path and the proposals, and ask which numbers to apply. Do not apply anything before they answer.

## 5. Apply and record

1. Apply only the approved proposals, and only to the targets above. Create `~/knowledge/review/local/` files as needed. Never edit `~/.agents/review`, `~/.agents/skills`, or `~/.files`, and never edit, commit, or open a PR in a repo. Repo-level proposals are appended to `~/knowledge/review/proposals.md` with the date and evidence.
2. If you changed anything under `~/knowledge/review/local/reviewers/` or `local/pre-pr.md`, run `review version` again. The version covers the shared prompts and these local files. Then append to `~/knowledge/review/CHANGES.md`:
   - the date
   - the old and new prompt versions
   - the proposals applied, each in one line
   - the metric each one should move

   The next retro uses `prompt_versions` in `stats` to compare before and after.
3. **Replay eval cases after prompt changes.** If reviewer prompts changed and `~/knowledge/review/evals/cases.jsonl` has cases, offer to replay up to 5 of them. Each replay costs a few subagent runs.
   - For each case, run `git rev-parse <merge_commit>^1` in a local clone of that repo. That commit is the `merge_base`, and the merge commit is the `head`.
   - Run the `bugs` reviewer (focus `diff`) and the `security` reviewer with `head` set, as `pre-pr` step 5 does, then run the verifier.
   - A case counts as caught if a confirmed finding points at what the revert undid.
   - Append `{"ts", "prompt_version", "repo", "pr", "caught", "finding"}` to `~/knowledge/review/evals/results.jsonl` and report the catch rate.
   - Only read with git (`git show`, `git diff`, `git rev-parse`). If the merge commit is missing locally, `git fetch origin` is fine. Never check out, commit, or create worktrees in a repo for this.
4. Mention the report path again in the final message, with the applied proposal numbers.
