#!/usr/bin/env bash
# preToolUse hook: warns (but does not block) when agents attempt to modify
# files in sdk/ or interface contract documents. Per R3, these changes require
# explicit human approval.
set -euo pipefail

input=$(cat)
file_path=$(echo "$input" | jq -r '.input.path // .input.filePath // empty' 2>/dev/null || echo "")

if [[ -z "$file_path" ]]; then
  echo '{"permission": "allow"}'
  exit 0
fi

is_protected=false

case "$file_path" in
  */sdk/*|*/SDK/*)
    is_protected=true
    ;;
  *interface-contract*|*interface_contract*)
    is_protected=true
    ;;
esac

if [[ "$is_protected" == "true" ]]; then
  echo '{
    "permission": "ask",
    "user_message": "This file is part of the SDK constraint surface or an interface contract. Codex Automata rule R3 requires explicit human approval before modifying these. Do you approve this change?",
    "agent_message": "A hook flagged this as a protected SDK/contract file. The user must approve changes per R3."
  }'
else
  echo '{"permission": "allow"}'
fi
exit 0
