# Verify: <repo>

<!-- Local to this machine, never committed. Agents run these checks before saying
     a task is done, and pre-pr runs them before review. The section names are parsed
     by ~/.agents/review/bin/review, so keep them as they are. -->

## Format

<!-- The edit hook runs the first matching command on every file an agent edits.
     Format: - `GLOB`: `COMMAND {file}`  ({file} is the path relative to the repo root;
     the command runs from the repo root). Only formatters that are safe to run
     unattended. Leave the section empty to turn the hook off for this repo. -->

## Checks

<!-- Run the rows whose "When" matches the change. Prefer commands scoped to the changed
     files when the tool supports it. -->

| Check | Command | When |
|---|---|---|
|  |  |  |

## Manual and UI checks

<!-- What to do when a change affects UI or behavior that the checks above don't cover
     (simulator, browser, screenshots), and which skill or doc explains how. -->

## Not runnable locally

<!-- Checks that only run in CI, so the agent says so instead of claiming they passed. -->
