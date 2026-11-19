#!/usr/bin/env bash
# Cursor sessionStart hook: inject the code review workflow rules, then this
# machine's local rules (if any), into the session's context.
python3 - "$HOME/.agents/review/RULES.md" "$HOME/knowledge/review/local/rules.md" <<'PY'
import json, os, sys
parts = [open(p).read() for p in sys.argv[1:] if os.path.exists(p)]
print(json.dumps({"additional_context": "\n\n".join(parts)}))
PY
