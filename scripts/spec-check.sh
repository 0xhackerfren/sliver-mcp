#!/usr/bin/env bash
set -euo pipefail

# Spec-before-code gate: verifies that every source module has a corresponding
# specification document. Exits non-zero if modules lack specs.
#
# Usage:
#   ./scripts/spec-check.sh [--src-dir src] [--spec-dir docs]
#
# Scans src-dir for module directories or files, then checks spec-dir for a
# matching spec document. Configurable via arguments.

SRC_DIR="src"
SPEC_DIR="docs"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --src-dir) SRC_DIR="$2"; shift 2 ;;
    --spec-dir) SPEC_DIR="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 2 ;;
  esac
done

echo "========================================="
echo " Codex Automata Spec Check"
echo "========================================="
echo "Source directory: $SRC_DIR"
echo "Spec directory:   $SPEC_DIR"
echo ""

if [[ ! -d "$SRC_DIR" ]]; then
  echo "Source directory '$SRC_DIR' not found. Nothing to check."
  exit 0
fi

if [[ ! -d "$SPEC_DIR" ]]; then
  echo "FAILED: Spec directory '$SPEC_DIR' does not exist."
  echo "  Codex Automata requires specifications before code."
  echo "  Create specs using templates/spec-template.md."
  exit 1
fi

missing=0
checked=0

# Check top-level module directories in src/
for module_dir in "$SRC_DIR"/*/; do
  [[ ! -d "$module_dir" ]] && continue
  module_name=$(basename "$module_dir")
  [[ "$module_name" == "__pycache__" || "$module_name" == "node_modules" || "$module_name" == ".git" ]] && continue

  checked=$((checked + 1))

  # Look for any spec document that references this module
  found=0
  for spec_file in "$SPEC_DIR"/*.md; do
    [[ ! -f "$spec_file" ]] && continue
    if grep -qi "$module_name" "$spec_file" 2>/dev/null; then
      found=1
      break
    fi
  done

  if [[ $found -eq 0 ]]; then
    echo "  [MISSING SPEC] Module '$module_name' in $SRC_DIR/ has no specification in $SPEC_DIR/"
    missing=$((missing + 1))
  fi
done

# If no module directories, check for top-level source files
if [[ $checked -eq 0 ]]; then
  for src_file in "$SRC_DIR"/*.{ts,tsx,js,jsx,py,go,rs,java} 2>/dev/null; do
    [[ ! -f "$src_file" ]] && continue
    checked=$((checked + 1))
  done

  if [[ $checked -gt 0 ]]; then
    spec_count=$(find "$SPEC_DIR" -name "*.md" -not -name "README.md" 2>/dev/null | wc -l)
    if [[ $spec_count -eq 0 ]]; then
      echo "  [MISSING SPEC] Source files exist in $SRC_DIR/ but no specifications found in $SPEC_DIR/"
      missing=1
    fi
  fi
fi

echo ""
if [[ $missing -gt 0 ]]; then
  echo "FAILED: $missing module(s) missing specifications."
  echo "  Codex Automata rule R1: Do not write implementation before the specification exists."
  echo "  Create specs using templates/spec-template.md."
  exit 1
elif [[ $checked -eq 0 ]]; then
  echo "PASSED: No source modules found. Nothing to check."
  exit 0
else
  echo "PASSED: All $checked module(s) have specifications."
  exit 0
fi
