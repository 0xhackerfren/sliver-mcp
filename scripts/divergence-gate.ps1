<#
.SYNOPSIS
  Divergence gate: scans source files for slop fingerprints.

.DESCRIPTION
  Scans source files for AI-default patterns (banned fonts, hardcoded colors,
  generic copy, structural anti-patterns) defined in the design identity or a
  default catalog. Exits non-zero when violations are found. Suitable for CI.

.PARAMETER Config
  Path to a JSON config file with custom fingerprints. Optional.

.PARAMETER Target
  Directory to scan. Defaults to src/, app/, lib/, or current directory.

.EXAMPLE
  .\scripts\divergence-gate.ps1
  .\scripts\divergence-gate.ps1 -Target src -Config divergence.json
#>
param(
    [string]$Config = "",
    [string]$Target = ""
)

$ErrorActionPreference = "Stop"

if (-not $Target) {
    if (Test-Path "src") { $Target = "src" }
    elseif (Test-Path "app") { $Target = "app" }
    elseif (Test-Path "lib") { $Target = "lib" }
    else { $Target = "." }
}

$Extensions = @("*.css","*.scss","*.less","*.ts","*.tsx","*.js","*.jsx","*.svelte","*.vue","*.html","*.astro")
$Violations = @()

function Find-Pattern {
    param([string]$Label, [string]$Regex)

    foreach ($ext in $Extensions) {
        $files = Get-ChildItem -Path $Target -Filter $ext -Recurse -File -ErrorAction SilentlyContinue
        foreach ($file in $files) {
            $lines = Get-Content $file.FullName -ErrorAction SilentlyContinue
            for ($i = 0; $i -lt $lines.Count; $i++) {
                if ($lines[$i] -match $Regex) {
                    $script:Violations += [PSCustomObject]@{
                        Pattern = $Label
                        File    = $file.FullName
                        Line    = ($i + 1)
                        Match   = $lines[$i].Trim().Substring(0, [Math]::Min($lines[$i].Trim().Length, 120))
                    }
                }
            }
        }
    }
}

function Run-DefaultCatalog {
    Write-Host "Running default slop fingerprint catalog against $Target ..."

    Find-Pattern "banned-font:Inter" "font-family[^;]*Inter"
    Find-Pattern "banned-font:Roboto" "font-family[^;]*Roboto"
    Find-Pattern "banned-font:Arial" "font-family[^;]*Arial"
    Find-Pattern "default-color:indigo-600" "(#4f46e5|indigo-600)"
    Find-Pattern "default-color:purple-blue-gradient" "gradient[^;]*(purple|indigo)[^;]*(blue|sky)"
    Find-Pattern "hardcoded-hex-color" "#[0-9a-fA-F]{3,8}"
    Find-Pattern "hardcoded-font-family" "font-family\s*:"
    Find-Pattern "hardcoded-px-value" ":\s*\d+px"
    Find-Pattern "hardcoded-rem-value" ":\s*\d+(\.\d+)?rem"
    Find-Pattern "banned-copy:unlock-the-power" "[Uu]nlock the power of"
    Find-Pattern "banned-copy:all-in-one-solution" "[Aa]ll-in-one solution"
    Find-Pattern "banned-copy:seamlessly-integrate" "[Ss]eamlessly integrate"
    Find-Pattern "banned-copy:something-went-wrong" "[Ss]omething went wrong"
    Find-Pattern "banned-naming:utils" "(utils\.(ts|js|tsx|jsx)|/utils/index)"
    Find-Pattern "banned-naming:helpers" "(helpers\.(ts|js|tsx|jsx)|/helpers/index)"
    Find-Pattern "banned-visual:glassmorphism" "(backdrop-filter|backdrop-blur)"
}

function Run-ConfigCatalog {
    Write-Host "Running divergence gate with config: $Config ..."
    $cfg = Get-Content $Config -Raw | ConvertFrom-Json
    foreach ($fp in $cfg.fingerprints) {
        Find-Pattern $fp.label $fp.pattern
    }
}

Write-Host "========================================="
Write-Host " Codex Automata Divergence Gate"
Write-Host "========================================="

if ($Config -and (Test-Path $Config)) {
    Run-ConfigCatalog
} else {
    Run-DefaultCatalog
}

Write-Host ""
if ($Violations.Count -gt 0) {
    Write-Host "FAILED: $($Violations.Count) slop fingerprint violation(s) found." -ForegroundColor Red
    foreach ($v in $Violations) {
        Write-Host "  [SLOP] $($v.File):$($v.Line) -- pattern '$($v.Pattern)' matched: $($v.Match)" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "Fix: Replace hardcoded values with design tokens from your SDK."
    Write-Host "     Remove banned patterns per your design identity document."
    exit 1
} else {
    Write-Host "PASSED: No slop fingerprints detected." -ForegroundColor Green
    exit 0
}
