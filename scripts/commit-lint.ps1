<#
.SYNOPSIS
  Commit message linter for spec-section traceability.

.DESCRIPTION
  Verifies commit messages reference a specification section, agent task, or
  use a recognized prefix. Suitable as a CI check.

.PARAMETER MessageFile
  Path to a file containing the commit message.

.PARAMETER Message
  Commit message string directly.

.EXAMPLE
  .\scripts\commit-lint.ps1 -Message "cast: implement login flow"
  git log -1 --format=%B | .\scripts\commit-lint.ps1 -MessageFile -
#>
param(
    [string]$MessageFile = "",
    [string]$Message = ""
)

$ErrorActionPreference = "Stop"

Write-Host "========================================="
Write-Host " Codex Automata Commit Lint"
Write-Host "========================================="

if ($MessageFile -and (Test-Path $MessageFile)) {
    $Message = Get-Content $MessageFile -Raw
} elseif (-not $Message) {
    Write-Host "Usage: commit-lint.ps1 -MessageFile <path> or -Message <string>"
    exit 0
}

$firstLine = ($Message -split "`n")[0].Trim()

if ($firstLine -match "^(Merge|fixup!|squash!|amend!|Revert)") {
    Write-Host "SKIP: Merge/fixup/revert commit."
    exit 0
}

$prefixes = "^(spec|sdk|mold|cast|contract|review|recovery|intake|arch|research|infra|docs|fix|chore|refactor):"

if ($firstLine -match $prefixes) {
    Write-Host "PASSED: Commit message has recognized prefix." -ForegroundColor Green
    exit 0
}

if ($Message -match "\[(SPEC|spec)[^\]]*\]") {
    Write-Host "PASSED: Commit message references a specification section." -ForegroundColor Green
    exit 0
}

if ($Message -match "\[(TASK|task)[^\]]*\]|task[:\-]\d+") {
    Write-Host "PASSED: Commit message references an agent task." -ForegroundColor Green
    exit 0
}

Write-Host "FAILED: Commit message lacks traceability." -ForegroundColor Red
Write-Host ""
Write-Host "  First line: $firstLine"
Write-Host ""
Write-Host "  Rule R7 requires commits traceable to specification sections."
Write-Host "  Use: a prefix (cast:), spec ref ([SPEC-auth-2.3]), or task ref ([TASK-001])."
Write-Host ""
Write-Host "  Valid prefixes: spec, sdk, mold, cast, contract, review, recovery,"
Write-Host "                  intake, arch, research, infra, docs, fix, chore, refactor"
exit 1
