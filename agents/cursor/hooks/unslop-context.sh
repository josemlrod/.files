#!/usr/bin/env bash
# Cursor sessionStart hook: inject the unslop writing rules into the session's system context.
SKILL="$HOME/.agents/skills/unslop/SKILL.md"
python3 - "$SKILL" <<'PY'
import json, sys, re
body = open(sys.argv[1]).read()
body = re.sub(r"\A---\n.*?\n---\n", "", body, flags=re.S)
ctx = ("# Writing style (always enforce): unslop\n"
       "Apply these rules to all prose you produce: chat replies, docs, commit messages, PR descriptions, comments.\n\n" + body)
print(json.dumps({"additional_context": ctx}))
PY
