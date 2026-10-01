param(
    [switch]$NoBuild
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

& (Join-Path $PSScriptRoot 'docker-preflight.ps1')
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$environmentFile = Join-Path $root '.env'
if (-not (Test-Path -LiteralPath $environmentFile)) {
    Copy-Item -LiteralPath (Join-Path $root '.env.example') -Destination $environmentFile
    Write-Host 'Created .env from .env.example. Replace development secrets before server deployment.' -ForegroundColor Yellow
}

Push-Location $root
try {
    $sourceCommit = (& git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $sourceCommit -notmatch '^[0-9a-f]{40}$') {
        throw 'Cannot determine the full source commit for the Docker build.'
    }
    $previousSourceCommit = $env:SOURCE_COMMIT
    $env:SOURCE_COMMIT = $sourceCommit
    $arguments = @('compose', 'up', '-d')
    if (-not $NoBuild) {
        $arguments += '--build'
    }
    & docker @arguments
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Compose startup failed.'
    }
    & docker compose ps
}
finally {
    $env:SOURCE_COMMIT = $previousSourceCommit
    Pop-Location
}

Write-Host 'DOCKER_STACK_STARTED: open http://localhost' -ForegroundColor Green
