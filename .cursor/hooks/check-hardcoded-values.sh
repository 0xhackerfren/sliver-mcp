teleport what is
can #!/usr/bin/env bash
# afterFileEdit hook: warns when edited files contain hardcoded visual values
# that should use design tokens instead. Non-blocking (advisory only).
set -euo pipefail

input=$(cat)
file_path=$(echo "$input" | jq -r '.filePath // .path // empty' 2>/dev/null || echo "")

if [[ -z "$file_path" ]]; then
  echo '{"additional_context": ""}'
  exit 0
fi

# Only check files likely to contain visual values
case "$file_path" in
  *.css|*.scss|*.less|*.tsx|*.jsx|*.svelte|*.vue|*.astro|*.html)
    ;;
  *)
    echo '{"additional_context": ""}'
    exit 0
    ;;
esac

warnings=""

if [[ -f "$file_path" ]]; then
  if grep -qE '#[0-9a-fA-F]{3,8}' "$file_path" 2>/dev/null; then
    warnings="${warnings}Hardcoded hex colors detected. "
  fi
  if grep -qE 'font-family\s*:' "$file_path" 2>/dev/null; then
    warnings="${warnings}Hardcoded font-family detected. "
  fi
  if grep -qE ':\s*[0-9]+px' "$file_path" 2>/dev/null; then
    warnings="${warnings}Hardcoded px values detected. "
  fi
fi

if [[ -n "$warnings" ]]; then
  msg="[Divergence Warning] ${warnings}Design tokens should be used for all visual values per R14 and the design identity. Run scripts/divergence-gate.sh for a full scan."
  echo "{\"additional_context\": \"${msg}\"}"
else
  echo '{"additional_context": ""}'
fi
exit 0
