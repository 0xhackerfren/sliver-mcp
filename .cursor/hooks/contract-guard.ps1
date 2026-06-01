# preToolUse hook: warns (but does not block) when agents attempt to modify
# files in sdk/ or interface contract documents. Per R3, these changes require
# explicit human approval.

$ErrorActionPreference = 'Stop'

$input_data = $input | ConvertFrom-Json -ErrorAction SilentlyContinue
if (-not $input_data) {
    $raw = [Console]::In.ReadToEnd()
    $input_data = $raw | ConvertFrom-Json -ErrorAction SilentlyContinue
}

$file_path = if ($input_data.input.path) { $input_data.input.path } elseif ($input_data.input.filePath) { $input_data.input.filePath } else { '' }

if (-not $file_path) {
    Write-Output '{"permission": "allow"}'
    exit 0
}

$is_protected = $false

if ($file_path -match '[/\\]sdk[/\\]' -or $file_path -match '[/\\]SDK[/\\]') {
    $is_protected = $true
}
if ($file_path -match 'interface[-_]contract') {
    $is_protected = $true
}

if ($is_protected) {
    $response = @{
        permission = 'ask'
        user_message = 'This file is part of the SDK constraint surface or an interface contract. Codex Automata rule R3 requires explicit human approval before modifying these. Do you approve this change?'
        agent_message = 'A hook flagged this as a protected SDK/contract file. The user must approve changes per R3.'
    } | ConvertTo-Json -Compress
    Write-Output $response
} else {
    Write-Output '{"permission": "allow"}'
}
exit 0
