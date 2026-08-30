param(
    [int]$Port = 3081
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$hostRoot = Join-Path $repoRoot "apps\deepseek-harness-host"
$workspace = Join-Path $repoRoot ".codex-evidence\deepseek-harness-workspace"
$env:DSH_HOME = Join-Path $repoRoot ".codex-evidence\deepseek-harness-home"

New-Item -ItemType Directory -Force -Path $workspace | Out-Null
if (-not (Test-Path (Join-Path $hostRoot "node_modules\.bin\dsh.cmd"))) {
    corepack pnpm install --dir $hostRoot --ignore-scripts
}

Write-Host "DeepSeek Harness: http://127.0.0.1:$Port"
& (Join-Path $hostRoot "node_modules\.bin\dsh.cmd") web --port $Port --no-open
