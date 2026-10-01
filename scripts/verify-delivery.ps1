$ErrorActionPreference = 'Stop'
$utf8 = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8

function Assert-FullSourceCommit {
    param([Parameter(Mandatory = $true)][string]$Commit)
    if ($Commit -cnotmatch '^[0-9a-f]{40}$') {
        throw 'SOURCE_COMMIT 必须是完整的 40 位小写 Git 提交号。'
    }
}

function Get-WebHealthEndpoint {
    param([Parameter(Mandatory = $true)]$WebService)
    $publisher = @($WebService.Publishers | Where-Object {
        $_.TargetPort -eq 80 -and $_.Protocol -eq 'tcp' -and $_.PublishedPort
    } | Select-Object -First 1)
    if ($publisher.Count -ne 1) { throw 'Web 服务没有已发布的 HTTP 端口。' }
    return "http://127.0.0.1:$($publisher[0].PublishedPort)/health"
}

if ($MyInvocation.InvocationName -eq '.') { return }

$root = Split-Path -Parent $PSScriptRoot
$expectedServices = @('minio', 'postgres', 'redis', 'api', 'web', 'worker')

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker command was not found.'
}

$previousSourceCommit = $env:SOURCE_COMMIT
Push-Location $root
try {
    $sourceCommit = (& git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw '无法确定当前源码提交号。' }
    Assert-FullSourceCommit -Commit $sourceCommit
    $env:SOURCE_COMMIT = $sourceCommit
    Write-Host '[1/6] Existing local verification' -ForegroundColor Cyan
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'verify-local.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'Existing local verification failed.' }

    Write-Host '[2/6] Docker Compose service state and health' -ForegroundColor Cyan
    $psLines = @(& docker compose ps --all --format json 2>$null)
    if ($LASTEXITCODE -ne 0) { throw 'Unable to inspect Docker Compose services.' }
    $serviceRows = @($psLines | Where-Object { $_ -and $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json })
    foreach ($service in $expectedServices) {
        $row = $serviceRows | Where-Object { $_.Service -eq $service } | Select-Object -First 1
        if (-not $row) { throw "Required service is missing: $service" }
        if ([string]$row.State -ne 'running') { throw "Required service is not running: $service" }
        $health = [string]$row.Health
        if ($health -and $health -ne 'healthy') { throw "Service health check is not healthy: $service" }
    }

    Write-Host '[3/6] API and web health endpoints' -ForegroundColor Cyan
    & docker compose exec -T api python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=10)' *> $null
    if ($LASTEXITCODE -ne 0) { throw 'API 容器内健康检查失败。' }
    $webRow = $serviceRows | Where-Object { $_.Service -eq 'web' } | Select-Object -First 1
    $webEndpoint = Get-WebHealthEndpoint -WebService $webRow
    $response = Invoke-WebRequest -UseBasicParsing -Uri $webEndpoint -TimeoutSec 10
    if ($response.StatusCode -ne 200) { throw "Web 健康检查未返回 HTTP 200：$webEndpoint" }

    Write-Host '[4/6] Production safety and Compose configuration' -ForegroundColor Cyan
    $productionExample = Join-Path $root '.env.production.example'
    if (-not (Test-Path -LiteralPath $productionExample -PathType Leaf)) {
        throw 'Production environment example is missing.'
    }

    $productionCompose = Join-Path $root 'compose.prod.yml'
    $apiLifecycle = Join-Path $root 'apps\api-server\app\core\lifecycle.py'
    foreach ($path in @($productionCompose, $apiLifecycle)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Production safety source is missing: $path"
        }
    }

    $productionComposeText = Get-Content -LiteralPath $productionCompose -Raw -Encoding UTF8
    $productionExampleText = Get-Content -LiteralPath $productionExample -Raw -Encoding UTF8

    $productionAppEnvMatches = [regex]::Matches($productionComposeText, '(?m)^\s+APP_ENV:\s*production\s*$')
    if ($productionAppEnvMatches.Count -lt 2) {
        throw 'Production Compose must force APP_ENV=production for both API and worker services.'
    }
    if ($productionComposeText -notmatch '(?m)^\s+INITIAL_ADMIN_PASSWORD:\s*\$\{INITIAL_ADMIN_PASSWORD:\?[^}]+\}\s*$') {
        throw 'Production Compose must require INITIAL_ADMIN_PASSWORD explicitly.'
    }
    if ($productionComposeText -notmatch '(?m)^\s+SEED_DEMO_DATA:\s*["'']?false["'']?\s*$') {
        throw 'Production Compose must force SEED_DEMO_DATA=false.'
    }

    $python = Join-Path $root 'apps\api-server\.venv\Scripts\python.exe'
    Push-Location (Join-Path $root 'apps\api-server')
    try {
        & $python -m unittest tests.test_verify_delivery_gate.DeliveryLifecycleSafetyTests.test_actual_lifecycle_guard_rejects_unsafe_production_settings
        if ($LASTEXITCODE -ne 0) { throw '实际生产启动安全闸门验证失败。' }
    }
    finally { Pop-Location }

    foreach ($field in @(
        'INITIAL_ADMIN_USERNAME=',
        'INITIAL_ADMIN_PASSWORD=',
        'INITIAL_ADMIN_DISPLAY_NAME=',
        'INITIAL_ADMIN_DEPARTMENT='
    )) {
        if ($productionExampleText -notmatch "(?m)^$([regex]::Escape($field))") {
            throw "Production environment template is missing one-time administrator field: $field"
        }
    }
    if ($productionExampleText -notmatch '(?m)^INITIAL_ADMIN_PASSWORD=.*CHANGE_ME.*$') {
        throw 'Production environment template must require replacement of the one-time administrator password.'
    }
    if ($productionExampleText -notmatch '(?m)^SEED_DEMO_DATA=false\s*$') {
        throw 'Production environment template must disable demo data seeding.'
    }

    & docker compose --env-file $productionExample -f (Join-Path $root 'docker-compose.yml') -f (Join-Path $root 'compose.prod.yml') config --quiet *> $null
    if ($LASTEXITCODE -ne 0) { throw 'Production Docker Compose configuration is invalid.' }

    Write-Host '[5/6] Delivery, backup, and restore artifacts' -ForegroundColor Cyan
    $requiredFiles = @(
        'compose.prod.yml',
        '.env.production.example',
        'deploy\backup.sh',
        'deploy\restore.sh',
        'deploy\preflight-production.sh',
        'deploy\server-deploy.md'
    )
    foreach ($relativePath in $requiredFiles) {
        if (-not (Test-Path -LiteralPath (Join-Path $root $relativePath) -PathType Leaf)) {
            throw "Required delivery artifact is missing: $relativePath"
        }
    }

    Write-Host '[6/6] Recent API, web, and worker error logs' -ForegroundColor Cyan
    $logLines = @(& docker compose logs --since 10m --no-color api web worker 2>&1)
    if ($LASTEXITCODE -ne 0) { throw 'Unable to inspect recent service logs.' }
    # Match service log levels and stack traces, but do not treat valid request
    # query values such as `level=error` as error-level log entries.
    $errorLines = @($logLines | Where-Object {
        $_ -match '(?i)\|\s*(ERROR|CRITICAL)(?:\s|:)|Traceback|(?:^|\s)Exception(?:\s|:)'
    })
    if ($errorLines.Count -gt 0) {
        throw "Recent service logs contain $($errorLines.Count) error-level line(s)."
    }
}
finally {
    $env:SOURCE_COMMIT = $previousSourceCommit
    Pop-Location
}

Write-Host 'VERIFY_DELIVERY_OK: local verification, six services, health endpoints, production safety, delivery artifacts, and recent logs passed.' -ForegroundColor Green
