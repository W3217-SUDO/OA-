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
    Pop-Location
}

Write-Host 'DOCKER_STACK_STARTED: open http://localhost' -ForegroundColor Green
