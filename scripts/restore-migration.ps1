param(
    [Parameter(Mandatory = $true)]
    [string]$TargetDirectory,
    [string]$PackageRoot = $PSScriptRoot
)

$ErrorActionPreference = 'Stop'
$PackageRoot = [System.IO.Path]::GetFullPath($PackageRoot)
$TargetDirectory = [System.IO.Path]::GetFullPath($TargetDirectory)
$projectSource = Join-Path $PackageRoot 'project'
if (-not (Test-Path -LiteralPath (Join-Path $projectSource 'docker-compose.yml'))) {
    throw "迁移包不完整，缺少 project/docker-compose.yml：$PackageRoot"
}
if (Test-Path -LiteralPath $TargetDirectory) {
    if (Get-ChildItem -LiteralPath $TargetDirectory -Force -ErrorAction SilentlyContinue | Select-Object -First 1) {
        throw "目标目录非空，为避免覆盖请使用新的空目录：$TargetDirectory"
    }
}
else {
    New-Item -ItemType Directory -Force -Path $TargetDirectory | Out-Null
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw '未找到 Docker，请先安装并启动 Docker Desktop。' }
& docker info | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop 尚未正常运行。' }

Write-Host '[1/8] 校验迁移包 SHA256' -ForegroundColor Cyan
$checksumFile = Join-Path $PackageRoot 'SHA256SUMS.txt'
if (Test-Path -LiteralPath $checksumFile) {
    foreach ($line in Get-Content -LiteralPath $checksumFile) {
        if (-not $line.Trim()) { continue }
        $parts = $line -split '  ',2
        $file = Join-Path $PackageRoot $parts[1]
        if (-not (Test-Path -LiteralPath $file)) { throw "缺少迁移文件：$($parts[1])" }
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $file).Hash -ne $parts[0]) { throw "校验失败：$($parts[1])" }
    }
}

Write-Host '[2/8] 复制项目源码' -ForegroundColor Cyan
& robocopy $projectSource $TargetDirectory /E /COPY:DAT /DCOPY:DAT /R:2 /W:1 /NFL /NDL /NJH /NJS /NP
if ($LASTEXITCODE -gt 7) { throw "项目复制失败，robocopy=$LASTEXITCODE" }

Write-Host '[3/8] 导入 Docker 镜像' -ForegroundColor Cyan
$imagesTar = Join-Path $PackageRoot 'docker-images.tar'
if (Test-Path -LiteralPath $imagesTar) {
    & docker load --input $imagesTar
    if ($LASTEXITCODE -ne 0) { throw 'Docker 镜像导入失败' }
}

Push-Location $TargetDirectory
try {
    if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
    if (& docker compose ps -a -q) {
        throw '当前 Compose 项目已存在容器。为避免覆盖已有数据，请换一个目录/项目名或先人工确认。'
    }

    Write-Host '[4/8] 创建基础容器与卷' -ForegroundColor Cyan
    & docker compose up -d postgres redis minio
    if ($LASTEXITCODE -ne 0) { throw '基础容器启动失败' }
    $deadline = (Get-Date).AddMinutes(2)
    do {
        $postgresId = (& docker compose ps -q postgres).Trim()
        $health = if ($postgresId) { & docker inspect --format='{{.State.Health.Status}}' $postgresId } else { '' }
        if ($health -eq 'healthy') { break }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    if ($health -ne 'healthy') { throw "PostgreSQL 未就绪：$health" }

    Write-Host '[5/8] 恢复 PostgreSQL' -ForegroundColor Cyan
    $dump = Join-Path $PackageRoot 'data\postgres\legal_platform.dump'
    if (Test-Path -LiteralPath $dump) {
        & docker cp $dump "${postgresId}:/tmp/legal_platform.dump"
        & docker exec $postgresId pg_restore -U legal -d legal_platform --clean --if-exists --no-owner --no-privileges /tmp/legal_platform.dump
        if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL 数据恢复失败' }
        & docker exec $postgresId rm -f /tmp/legal_platform.dump | Out-Null
    }

    Write-Host '[6/8] 恢复 MinIO 和附件（Redis 使用新建空卷）' -ForegroundColor Cyan
    $minioId = (& docker compose ps -q minio).Trim()
    & docker compose stop minio | Out-Null
    $minioData = Join-Path $PackageRoot 'data\minio'
    if (Test-Path -LiteralPath $minioData) { & docker cp "$minioData\." "${minioId}:/data" }
    & docker compose start minio | Out-Null

    & docker compose create api | Out-Null
    $apiId = (& docker compose ps -a -q api).Trim()
    $uploadsData = Join-Path $PackageRoot 'data\uploads'
    if (Test-Path -LiteralPath $uploadsData) { & docker cp "$uploadsData\." "${apiId}:/app/uploads" }

    Write-Host '[7/8] 启动完整系统' -ForegroundColor Cyan
    & docker compose up -d api worker web
    if ($LASTEXITCODE -ne 0) { throw '完整系统启动失败' }
    $deadline = (Get-Date).AddMinutes(3)
    do {
        $apiId = (& docker compose ps -q api).Trim()
        $webId = (& docker compose ps -q web).Trim()
        $apiHealth = if ($apiId) { & docker inspect --format='{{.State.Health.Status}}' $apiId } else { '' }
        $webHealth = if ($webId) { & docker inspect --format='{{.State.Health.Status}}' $webId } else { '' }
        if ($apiHealth -eq 'healthy' -and $webHealth -eq 'healthy') { break }
        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $deadline)
    if ($apiHealth -ne 'healthy' -or $webHealth -ne 'healthy') { throw "服务未就绪：api=$apiHealth web=$webHealth" }

    Write-Host '[8/8] 恢复完成' -ForegroundColor Green
    & docker compose ps
}
finally {
    Pop-Location
}

Write-Host '请打开 http://127.0.0.1/，并按 project/docs/新电脑恢复与继续开发.md 运行验收。' -ForegroundColor Green
