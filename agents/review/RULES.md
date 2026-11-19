# Code review workflow (always on, every repo)

Personal setup. The engine is in `~/.agents/review`, linked from the `.files` repo. Review data and this machine's own rules are in `~/knowledge/review`, which no repo contains. Never add either to a project repo. Rules in `~/knowledge/review/local/rules.md` are loaded after these and win where they conflict.

- **Show proof before "done".** Before you say a coding task is finished, run the checks that apply from `~/knowledge/review/<repo>/verify.md` (or the repo's own lint, type, and test commands if that file is missing) and show each command with its result. If you could not run a check, say which one and why. Never say a check passed if you did not run it.
- **Review before pushing.** Run the `pre-pr` skill (`~/.agents/skills/pre-pr/SKILL.md`) before `git push` or `gh pr create`. A hook blocks both until a review round passes for the exact code being pushed. After any new commit, run `pre-pr` again; it only reviews what changed.
- **Never get around the gate.** Only run `~/.agents/review/bin/review skip` when the user tells you, in this conversation, to skip review for this push. Do not create `~/knowledge/review/GATE_OFF` and do not push in a way meant to avoid the hook.
- **Rounds must converge.** Fix every place a reported bug class appears, not just the reported line. After 3 failed rounds in a row, stop and discuss the approach with the user.
- **Record dismissed findings.** When the user rejects or waves off a review finding, record it with `~/.agents/review/bin/review outcome`.
- **Check absolute claims in comments.** Before committing a comment that says "only", "every", "always", or "never", grep the callers and confirm it holds for each one. If one exception exists, name it or drop the absolute.
