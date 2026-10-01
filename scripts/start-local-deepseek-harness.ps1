param(
    [ValidateRange(1, 65535)]
    [int]$Port = 3081
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$hostRoot = Join-Path $repoRoot "apps\deepseek-harness-host"
if (-not $env:DSH_HOME) {
    $env:DSH_HOME = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Sunhold\deepseek-harness'
}
if (-not (Test-Path (Join-Path $hostRoot "node_modules\.bin\dsh.cmd"))) {
    corepack pnpm install --dir $hostRoot --frozen-lockfile --ignore-scripts
    if ($LASTEXITCODE -ne 0) { throw 'DeepSeek Harness dependency installation failed.' }
}

Write-Host "DeepSeek Harness: http://127.0.0.1:$Port"
$previousPort = $env:DSH_PORT
$env:DSH_PORT = [string]$Port
try {
    & node (Join-Path $hostRoot 'scripts\start.mjs')
    if ($LASTEXITCODE -ne 0) { throw 'DeepSeek Harness startup failed.' }
}
finally {
    $env:DSH_PORT = $previousPort
}
