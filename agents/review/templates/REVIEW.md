# Review rules: <repo>

<!-- Local to this machine, never committed. The pre-pr reviewers read this file.
     Keep it under about 80 lines. The section names below are parsed by
     ~/.agents/review/bin/review, so keep them as they are. -->

## What counts as a failure

<!-- The few outcomes in this repo that are worse than any style issue.
     Examples: "a migration that can't be rolled back", "docs that describe behavior the code doesn't have". -->

- 

## High-risk paths

<!-- One glob per line, in backticks. A change touching any of these gets the high review tier
     and a note in the PR draft that a human must review it. -->

- `.github/workflows/**`

## Ignored paths

<!-- One glob per line, in backticks. Reviewers skip these files (generated code, snapshots, lockfiles). -->

- 

## Conventions to check

<!-- Repo rules a reviewer can verify in a diff. Point to the doc that defines each one. -->

- 

## Do not flag

- Formatting and style that the formatter or linter already enforces.
- 

## Known bug-prone areas

<!-- Places where past reverts or incidents came from, with the PR or commit if known. -->

- 
