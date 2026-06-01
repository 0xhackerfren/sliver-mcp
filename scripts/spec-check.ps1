<#
.SYNOPSIS
  Spec-before-code gate: verifies every source module has a specification.

.DESCRIPTION
  Scans the source directory for modules and checks the spec directory for
  matching specification documents. Exits non-zero if specs are missing.

.PARAMETER SrcDir
  Source directory to scan. Default: src

.PARAMETER SpecDir
  Specification directory to check. Default: docs
#>
param(
    [string]$SrcDir = "src",
    [string]$SpecDir = "docs"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================="
Write-Host " Codex Automata Spec Check"
Write-Host "========================================="
Write-Host "Source directory: $SrcDir"
Write-Host "Spec directory:   $SpecDir"
Write-Host ""

if (-not (Test-Path $SrcDir)) {
    Write-Host "Source directory '$SrcDir' not found. Nothing to check."
    exit 0
}

if (-not (Test-Path $SpecDir)) {
    Write-Host "FAILED: Spec directory '$SpecDir' does not exist." -ForegroundColor Red
    Write-Host "  Codex Automata requires specifications before code."
    exit 1
}

$missing = 0
$checked = 0

$moduleDirs = Get-ChildItem -Path $SrcDir -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -notin @("__pycache__", "node_modules", ".git") }

foreach ($dir in $moduleDirs) {
    $checked++
    $moduleName = $dir.Name
    $found = $false

    $specFiles = Get-ChildItem -Path $SpecDir -Filter "*.md" -File -ErrorAction SilentlyContinue
    foreach ($spec in $specFiles) {
        $content = Get-Content $spec.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -match [regex]::Escape($moduleName)) {
            $found = $true
            break
        }
    }

    if (-not $found) {
        Write-Host "  [MISSING SPEC] Module '$moduleName' in $SrcDir/ has no specification in $SpecDir/" -ForegroundColor Yellow
        $missing++
    }
}

if ($checked -eq 0) {
    $srcFiles = Get-ChildItem -Path $SrcDir -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in @(".ts",".tsx",".js",".jsx",".py",".go",".rs",".java") }

    if ($srcFiles.Count -gt 0) {
        $checked = $srcFiles.Count
        $specCount = (Get-ChildItem -Path $SpecDir -Filter "*.md" -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -ne "README.md" }).Count

        if ($specCount -eq 0) {
            Write-Host "  [MISSING SPEC] Source files exist but no specifications found in $SpecDir/" -ForegroundColor Yellow
            $missing = 1
        }
    }
}

Write-Host ""
if ($missing -gt 0) {
    Write-Host "FAILED: $missing module(s) missing specifications." -ForegroundColor Red
    Write-Host "  Rule R1: Do not write implementation before the specification exists."
    exit 1
} elseif ($checked -eq 0) {
    Write-Host "PASSED: No source modules found. Nothing to check." -ForegroundColor Green
    exit 0
} else {
    Write-Host "PASSED: All $checked module(s) have specifications." -ForegroundColor Green
    exit 0
}
