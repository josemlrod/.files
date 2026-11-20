#!/usr/bin/env bash
# Injects the unslop writing rules into Claude Code context.
#   session -> full SKILL.md body (SessionStart: startup, resume, clear, compact)
#   prompt  -> one-line reminder (UserPromptSubmit)
SKILL="$HOME/.agents/skills/unslop/SKILL.md"
case "${1:-session}" in
  session)
    echo "# Writing style (always enforce): unslop"
    echo "Apply these rules to all prose you produce: chat replies, docs, commit messages, PR descriptions, comments."
    echo
    # strip YAML frontmatter
    awk 'BEGIN{fm=0} NR==1 && /^---$/ {fm=1; next} fm==1 && /^---$/ {fm=0; next} fm==0 {print}' "$SKILL"
    ;;
  prompt)
    echo "Reminder: apply the unslop writing rules (already in context from session start) to every piece of prose in this response."
    ;;
esac
exit 0
