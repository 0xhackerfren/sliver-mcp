#!/usr/bin/env bash
set -euo pipefail

# Divergence gate: scans source files for slop fingerprints defined in the
# project's design identity document or a default catalog. Exits non-zero
# when violations are found, suitable for CI quality gates.
#
# Usage:
#   ./scripts/divergence-gate.sh [--config path/to/divergence.json] [target-dir]
#
# Without --config, uses the default fingerprint catalog below.
# target-dir defaults to src/ if it exists, otherwise the current directory.

CONFIG=""
TARGET=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    *) TARGET="$1"; shift ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  if [[ -d "src" ]]; then TARGET="src"
  elif [[ -d "app" ]]; then TARGET="app"
  elif [[ -d "lib" ]]; then TARGET="lib"
  else TARGET="."; fi
fi

EXTENSIONS="css,scss,less,ts,tsx,js,jsx,svelte,vue,html,astro"

violations=0
violation_log=""

add_violation() {
  local pattern="$1" file="$2" line="$3" match="$4"
  violations=$((violations + 1))
  violation_log="${violation_log}\n  [SLOP] ${file}:${line} -- pattern '${pattern}' matched: ${match}"
}

scan_pattern() {
  local label="$1"
  local regex="$2"

  while IFS=: read -r file lineno content; do
    [[ -z "$file" ]] && continue
    add_violation "$label" "$file" "$lineno" "$(echo "$content" | sed 's/^[[:space:]]*//' | head -c 120)"
  done < <(rg --no-heading --line-number --glob "*.{${EXTENSIONS}}" \
    -e "$regex" "$TARGET" 2>/dev/null || true)
}

# --- Default slop fingerprint catalog ---
# These run unless a config file overrides them.

run_default_catalog() {
  echo "Running default slop fingerprint catalog against $TARGET ..."

  # Banned fonts (body/primary context)
  scan_pattern "banned-font:Inter" "font-family[^;]*Inter"
  scan_pattern "banned-font:Roboto" "font-family[^;]*Roboto"
  scan_pattern "banned-font:Arial" "font-family[^;]*['\"]?Arial['\"]?"

  # Hardcoded AI-default colors
  scan_pattern "default-color:indigo-600" "(#4f46e5|indigo-600|bg-indigo-600|text-indigo-600)"
  scan_pattern "default-color:purple-blue-gradient" "gradient[^;]*(purple|indigo)[^;]*(blue|sky)"
  scan_pattern "default-color:violet-500" "(#8b5cf6|violet-500)"

  # Hardcoded visual values (should use design tokens)
  scan_pattern "hardcoded-hex-color" "(?<!--)(?<!\/\/)(?<!\*)#[0-9a-fA-F]{3,8}(?![-\w])"
  scan_pattern "hardcoded-font-family" "font-family\s*:"
  scan_pattern "hardcoded-px-value" ":\s*\d+px"
  scan_pattern "hardcoded-rem-value" ":\s*\d+(\.\d+)?rem"

  # Banned copy patterns
  scan_pattern "banned-copy:unlock-the-power" "[Uu]nlock the power of"
  scan_pattern "banned-copy:all-in-one-solution" "[Aa]ll-in-one solution"
  scan_pattern "banned-copy:seamlessly-integrate" "[Ss]eamlessly integrate"
  scan_pattern "banned-copy:something-went-wrong" "[Ss]omething went wrong"

  # Banned structural patterns (class/component-level heuristics)
  scan_pattern "banned-naming:utils" "(utils\.(ts|js|tsx|jsx)|/utils/index)"
  scan_pattern "banned-naming:helpers" "(helpers\.(ts|js|tsx|jsx)|/helpers/index)"

  # Glassmorphism / blur backgrounds
  scan_pattern "banned-visual:glassmorphism" "(backdrop-filter|backdrop-blur|bg-opacity-)"

  # Generic hero icon circles
  scan_pattern "banned-visual:icon-circles" "rounded-full[^\"]*bg-"
}

run_config_catalog() {
  echo "Running divergence gate with config: $CONFIG ..."

  if ! command -v jq &>/dev/null; then
    echo "ERROR: jq is required when using --config. Install jq or use the default catalog."
    exit 2
  fi

  local count
  count=$(jq '.fingerprints | length' "$CONFIG")

  for i in $(seq 0 $((count - 1))); do
    local label regex
    label=$(jq -r ".fingerprints[$i].label" "$CONFIG")
    regex=$(jq -r ".fingerprints[$i].pattern" "$CONFIG")
    scan_pattern "$label" "$regex"
  done
}

echo "========================================="
echo " Codex Automata Divergence Gate"
echo "========================================="

if [[ -n "$CONFIG" && -f "$CONFIG" ]]; then
  run_config_catalog
else
  run_default_catalog
fi

echo ""
if [[ $violations -gt 0 ]]; then
  echo "FAILED: $violations slop fingerprint violation(s) found."
  echo -e "$violation_log"
  echo ""
  echo "Fix: Replace hardcoded values with design tokens from your SDK."
  echo "     Remove banned patterns per your design identity document."
  echo "     See templates/design-identity-template.md for guidance."
  exit 1
else
  echo "PASSED: No slop fingerprints detected."
  exit 0
fi
