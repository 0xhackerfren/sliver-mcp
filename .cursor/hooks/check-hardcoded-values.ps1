# afterFileEdit hook: warns when edited files contain hardcoded visual values
# that should use design tokens instead. Non-blocking (advisory only).

$ErrorActionPreference = 'Stop'

$input_data = $input | ConvertFrom-Json -ErrorAction SilentlyContinue
if (-not $input_data) {
    $raw = [Console]::In.ReadToEnd()
    $input_data = $raw | ConvertFrom-Json -ErrorAction SilentlyContinue
}

$file_path = if ($input_data.filePath) { $input_data.filePath } elseif ($input_data.path) { $input_data.path } else { '' }

if (-not $file_path) {
    Write-Output '{"additional_context": ""}'
    exit 0
}

$extensions = @('.css', '.scss', '.less', '.tsx', '.jsx', '.svelte', '.vue', '.astro', '.html')
$ext = [System.IO.Path]::GetExtension($file_path)
if ($ext -notin $extensions) {
    Write-Output '{"additional_context": ""}'
    exit 0
}

$warnings = ''

if (Test-Path $file_path) {
    $content = Get-Content $file_path -Raw -ErrorAction SilentlyContinue
    if ($content) {
        if ($content -match '#[0-9a-fA-F]{3,8}') {
            $warnings += 'Hardcoded hex colors detected. '
        }
        if ($content -match 'font-family\s*:') {
            $warnings += 'Hardcoded font-family detected. '
        }
        if ($content -match ':\s*[0-9]+px') {
            $warnings += 'Hardcoded px values detected. '
        }
    }
}

if ($warnings) {
    $msg = "[Divergence Warning] ${warnings}Design tokens should be used for all visual values per R14 and the design identity. Run scripts/divergence-gate.ps1 for a full scan."
    Write-Output "{`"additional_context`": `"$msg`"}"
} else {
    Write-Output '{"additional_context": ""}'
}
exit 0
