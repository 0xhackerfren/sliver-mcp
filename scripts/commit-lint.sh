#!/usr/bin/env bash
set -euo pipefail

# Commit message linter: verifies that commit messages reference a specification
# section or are tagged with a recognized prefix. Designed as a commit-msg hook
# or CI check.
#
# Usage:
#   As git hook:  cp scripts/commit-lint.sh .git/hooks/commit-msg && chmod +x .git/hooks/commit-msg
#   In CI:        echo "$COMMIT_MSG" | ./scripts/commit-lint.sh --stdin
#   Direct:       ./scripts/commit-lint.sh "path/to/commit-msg-file"

echo "========================================="
echo " Codex Automata Commit Lint"
echo "========================================="

MSG=""

if [[ "${1:-}" == "--stdin" ]]; then
  MSG=$(cat)
elif [[ -n "${1:-}" && -f "$1" ]]; then
  MSG=$(cat "$1")
else
  echo "Usage: commit-lint.sh <commit-msg-file> or commit-lint.sh --stdin"
  echo "  As git hook: copy to .git/hooks/commit-msg"
  exit 0
fi

# Skip merge commits and fixup commits
if echo "$MSG" | head -1 | grep -qiE "^(Merge|fixup!|squash!|amend!|Revert)"; then
  echo "SKIP: Merge/fixup/revert commit. No lint required."
  exit 0
fi

FIRST_LINE=$(echo "$MSG" | head -1)

# Recognized prefixes that indicate traceability
# spec: specification work
# sdk: SDK constraint surface changes
# mold: test molding
# cast: code casting (implementation)
# contract: interface contract changes
# review: review-related changes
# recovery: gap recovery
# intake: project intake
# arch: architecture decisions
# research: research artifacts
# infra: infrastructure/CI/deployment
# docs: documentation
# fix: bug fix (should still reference spec)
PREFIXES="^(spec|sdk|mold|cast|contract|review|recovery|intake|arch|research|infra|docs|fix|chore|refactor):"

# Check for recognized prefix
if echo "$FIRST_LINE" | grep -qiE "$PREFIXES"; then
  echo "PASSED: Commit message has recognized prefix."
  exit 0
fi

# Check for spec section reference (e.g., [SPEC-auth-2.3] or [spec:auth:2.3])
if echo "$MSG" | grep -qiE "\[(SPEC|spec)[^]]*\]"; then
  echo "PASSED: Commit message references a specification section."
  exit 0
fi

# Check for task reference (e.g., [TASK-001] or task:001)
if echo "$MSG" | grep -qiE "\[(TASK|task)[^]]*\]|task[:-]\d+"; then
  echo "PASSED: Commit message references an agent task."
  exit 0
fi

echo "FAILED: Commit message lacks traceability."
echo ""
echo "  First line: $FIRST_LINE"
echo ""
echo "  Codex Automata rule R7 requires commits traceable to specification sections."
echo "  Use one of:"
echo "    - A prefix:       cast: implement user authentication"
echo "    - A spec ref:     [SPEC-auth-2.3] add password validation"
echo "    - A task ref:     [TASK-001] complete login flow"
echo ""
echo "  Valid prefixes: spec, sdk, mold, cast, contract, review, recovery,"
echo "                  intake, arch, research, infra, docs, fix, chore, refactor"
exit 1
