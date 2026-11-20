# Shared reviewer instructions

Every reviewer prompt in this folder starts by reading this file.

## Inputs from the caller

- `root`: the repo root. Run every command from there.
- `merge_base`: the commit the branch starts from.
- `files_to_review`: the only files you report on. On an incremental round this is just what changed since the last round.
- `incremental_from_tree`: set on incremental rounds. `git diff <incremental_from_tree> -- <file>` shows what changed since the last review. Review those changes, not the whole branch again.
- `intent`: what the change is supposed to do (PR description, task, or commit messages).
- `review_md`: the repo's local review rules. Read it first if it is set.
- `known_findings`: findings already reported on this branch. Never report them again, even reworded.

- `head`: usually unset. When set (replaying an old PR for the eval set), review the committed range `git diff <merge_base> <head> -- <files>` and read files with `git show <head>:<path>`, not from the working tree.

See the change with `git diff <merge_base> -- <files>`. That includes uncommitted work. Read the whole file around each hunk, and the callers or callees you need to judge it. A diff alone is not enough context.

## What not to report

- Formatting, naming, and style that a formatter or linter enforces.
- Anything under "Ignored paths" or "Do not flag" in `review_md`.
- Speculation you could check but didn't. Open the file and check it.
- Suggestions that make the code different but not more correct.
- A decision the `intent` states as deliberate: scope limits, deploy or merge order, a client contract chosen on purpose. Report it only if the code does not do what the intent says, or if the intent's own reasoning is wrong in a way you can show from the code.

## Output

Reply with one fenced `json` block holding an array, and nothing else after it. Use `[]` when you found nothing. Each item:

```json
{
  "file": "path/from/repo/root.ts",
  "line": 42,
  "class": "one or two words naming the kind of bug, e.g. null-handling, auth-bypass, stale-doc",
  "title": "One sentence stating the defect",
  "detail": "Concrete inputs or state, what happens, and why that is wrong. Cite the code you read.",
  "fix": "The smallest change that fixes it. If the same mistake appears elsewhere, name every place.",
  "severity": "important | nit",
  "in_diff": true
}
```

- `file` and `line` must point at a real line you read. Never guess a path.
- `important` means it will cause wrong behavior, data loss, a security hole, a broken build, or violates "What counts as a failure" in `review_md`. Everything else is `nit`. Use `nit` sparingly: an agent author pays a full review round for each one.
- `in_diff` is false when the problem is in code this branch didn't add or change. The caller labels those pre-existing.
- Report the class of a bug once with every location, not one finding per line.
