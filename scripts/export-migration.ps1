param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$TargetDirectory,
    [switch]$CreateZip
)

$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$TargetDirectory = [System.IO.Path]::GetFullPath($TargetDirectory)
$zipPath = "$TargetDirectory.zip"
$outputCreated = $false
$locationPushed = $false
$postgresId = $null
$originalRunningAppServices = @()
$appStopAttempted = $false

function Test-SensitivePackagePath {
    param([Parameter(Mandatory = $true)][string]$RelativePath)

    $normalized = $RelativePath.Replace('/', '\').TrimStart('\')
    $segments = @($normalized -split '\\' | Where-Object { $_ })
    if ($segments.Count -eq 0) { return $false }

    $blockedDirectories = @(
        '.git', '.venv', 'node_modules', 'dist', '__pycache__', 'sfhc',
        'backup', 'backups', 'log', 'logs', 'tmp', 'temp',
        '.pytest_cache', '.mypy_cache', '.ruff_cache', '.cache'
    )
    foreach ($segment in $segments[0..([Math]::Max(0, $segments.Count - 2))]) {
        if ($blockedDirectories -contains $segment.ToLowerInvariant()) { return $true }
    }

    $leaf = $segments[-1].ToLowerInvariant()
    if ($leaf -eq '.env.example' -or $leaf -eq '.env.production.example') { return $false }
    if ($leaf -eq '.env' -or $leaf.StartsWith('.env.')) { return $true }
    if ($leaf -eq 'postgres_globals.sql') { return $true }
    if ($leaf -match '^(id_rsa|id_ed25519)(\.|$)') { return $true }
    if ($leaf -match '\.(key|pem|p12|pfx|ppk|jks|keystore|kdbx)$') { return $true }
    if ($leaf -match '\.(log|tmp|temp|bak|old|swp|swo|dmp|pyc|pyo)$') { return $true }

    # 数据目录中可能包含用户上传的合法 ZIP；项目源码和包根目录中的旧 ZIP 必须排除。
    if ($leaf.EndsWith('.zip') -and $normalized -notmatch '(^|\\)data\\') { return $true }
    return $false
}

function Assert-NoSensitiveFiles {
    param(
        [Parameter(Mandatory = $true)][string]$ScanRoot,
        [Parameter(Mandatory = $true)][string]$Phase
    )

    $hits = @()
    if (Test-Path -LiteralPath $ScanRoot) {
        foreach ($item in Get-ChildItem -LiteralPath $ScanRoot -Recurse -Force) {
            $relative = $item.FullName.Substring($ScanRoot.Length).TrimStart('\')
            if (Test-SensitivePackagePath -RelativePath $relative) {
                $hits += $relative
                if ($hits.Count -ge 20) { break }
            }
        }
    }
    if ($hits.Count -gt 0) {
        throw "$Phase 敏感文件名扫描失败：$($hits -join '; ')"
    }
}

function Assert-ZipHasNoSensitiveFiles {
    param([Parameter(Mandatory = $true)][string]$ArchivePath)

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($ArchivePath)
    try {
        $hits = @()
        foreach ($entry in $archive.Entries) {
            if (Test-SensitivePackagePath -RelativePath $entry.FullName) {
                $hits += $entry.FullName
                if ($hits.Count -ge 20) { break }
            }
        }
        if ($hits.Count -gt 0) {
            throw "压缩后敏感文件名扫描失败：$($hits -join '; ')"
        }
    }
    finally {
        $archive.Dispose()
    }
}

if (-not [System.IO.Path]::IsPathRooted($TargetDirectory) -or $TargetDirectory.StartsWith('\\')) {
    throw '必须显式指定本机磁盘上的绝对目标目录，不允许网络共享路径。'
}
$sourcePrefix = $root.TrimEnd('\') + '\'
if ($TargetDirectory.Equals($root, [System.StringComparison]::OrdinalIgnoreCase) -or
    $TargetDirectory.StartsWith($sourcePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw '迁移目标目录不能位于项目源码目录内。'
}
if (Test-Path -LiteralPath $TargetDirectory) {
    throw "迁移目标目录已存在，为避免覆盖请更换目录：$TargetDirectory"
}
if (Test-Path -LiteralPath $zipPath) {
    throw "迁移 ZIP 已存在，为避免覆盖请更换目录：$zipPath"
}

Write-Warning '迁移包包含明文业务数据库和附件，本脚本不提供加密。请仅指定受当前用户保护的本机目录，并通过组织批准的加密介质或加密通道传输；ZIP 仅压缩，不等于加密。'

try {
    $projectTarget = Join-Path $TargetDirectory 'project'
    $dataTarget = Join-Path $TargetDirectory 'data'
    $postgresTarget = Join-Path $dataTarget 'postgres'
    $minioTarget = Join-Path $dataTarget 'minio'
    $uploadsTarget = Join-Path $dataTarget 'uploads'
    New-Item -ItemType Directory -Force -Path $projectTarget,$postgresTarget,$minioTarget,$uploadsTarget | Out-Null
    $outputCreated = $true

    Write-Host '[1/7] 复制项目源码与文档' -ForegroundColor Cyan
    $excludeDirs = @(
        '.git','.venv','node_modules','dist','__pycache__','sfhc',
        'backup','backups','log','logs','tmp','temp',
        '.pytest_cache','.mypy_cache','.ruff_cache','.cache'
    )
    $excludeFiles = @(
        '.env','.env.*','postgres_globals.sql','*.pyc','*.pyo','*.log','*.tmp','*.temp',
        '*.bak','*.old','*.swp','*.swo','*.dmp','*.zip',
        '*.key','*.pem','*.p12','*.pfx','*.ppk','*.jks','*.keystore','*.kdbx',
        'id_rsa','id_rsa.*','id_ed25519','id_ed25519.*'
    )
    & robocopy $root $projectTarget /E /COPY:DAT /DCOPY:DAT /R:2 /W:1 /XD $excludeDirs /XF $excludeFiles /NFL /NDL /NJH /NJS /NP
    if ($LASTEXITCODE -gt 7) { throw "项目复制失败，robocopy=$LASTEXITCODE" }

    # 第一遍显式排除所有 .env*；第二遍只恢复两个安全的示例配置文件。
    $safeEnvExamples = @('.env.example', '.env.production.example')
    & robocopy $root $projectTarget @safeEnvExamples /S /COPY:DAT /DCOPY:DAT /R:2 /W:1 /XD $excludeDirs /NFL /NDL /NJH /NJS /NP
    if ($LASTEXITCODE -gt 7) { throw "环境示例文件复制失败，robocopy=$LASTEXITCODE" }
    Assert-NoSensitiveFiles -ScanRoot $projectTarget -Phase '源码复制后'

    Push-Location $root
    $locationPushed = $true
    $services = @('postgres','redis','minio','api','worker','web')
    $requiredDataServices = @('postgres','minio')
    foreach ($service in $requiredDataServices) {
        if (-not (& docker compose ps -q $service)) { throw "容器未运行或不存在：$service" }
    }

    $postgresId = (& docker compose ps -q postgres).Trim()
    $minioId = (& docker compose ps -q minio).Trim()
    $apiId = (& docker compose ps -a -q api).Trim()
    if (-not $apiId) { throw 'API 容器不存在，无法复制上传附件。' }

    $appServices = @('web','worker','api')
    foreach ($service in $appServices) {
        if ((& docker compose ps -q $service).Trim()) {
            $originalRunningAppServices += $service
        }
    }
    if ($originalRunningAppServices.Count -gt 0) {
        Write-Host "停止写入服务以取得一致快照：$($originalRunningAppServices -join ', ')" -ForegroundColor Yellow
        $appStopAttempted = $true
        & docker compose stop @originalRunningAppServices
        if ($LASTEXITCODE -ne 0) { throw '停止应用服务失败' }
    }

    Write-Host '[2/7] 导出 PostgreSQL' -ForegroundColor Cyan
    & docker exec $postgresId pg_dump -U legal -d legal_platform -Fc -f /tmp/legal_platform.dump
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL pg_dump 失败' }
    & docker cp "${postgresId}:/tmp/legal_platform.dump" (Join-Path $postgresTarget 'legal_platform.dump')
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL 数据库文件复制失败' }
    & docker exec $postgresId rm -f /tmp/legal_platform.dump | Out-Null

    Write-Host '[3/7] Redis 不迁移（新环境空启动，避免重放旧 Celery 队列）' -ForegroundColor Cyan

    Write-Host '[4/7] 导出 MinIO 与上传附件' -ForegroundColor Cyan
    & docker cp "${minioId}:/data/." $minioTarget
    if ($LASTEXITCODE -ne 0) { throw 'MinIO 数据复制失败' }
    & docker cp "${apiId}:/app/uploads/." $uploadsTarget
    if ($LASTEXITCODE -ne 0) { throw '上传附件复制失败' }

    if ($appStopAttempted -and $originalRunningAppServices.Count -gt 0) {
        Write-Host "一致快照完成，恢复原运行服务：$($originalRunningAppServices -join ', ')" -ForegroundColor Yellow
        & docker compose start @originalRunningAppServices
        if ($LASTEXITCODE -ne 0) { throw '恢复应用服务失败' }
        $appStopAttempted = $false
    }

    Write-Host '[5/7] 导出 Docker 镜像' -ForegroundColor Cyan
    $images = @(
        'sunhold-legal-platform-api:latest',
        'sunhold-legal-platform-worker:latest',
        'sunhold-legal-platform-web:latest',
        'pgvector/pgvector:pg16',
        'redis:7.4-alpine',
        'minio/minio:latest'
    )
    & docker save --output (Join-Path $TargetDirectory 'docker-images.tar') @images
    if ($LASTEXITCODE -ne 0) { throw 'Docker 镜像导出失败' }

    Write-Host '[6/7] 生成清单与恢复入口' -ForegroundColor Cyan
    Copy-Item -LiteralPath (Join-Path $root 'scripts\restore-migration.ps1') -Destination (Join-Path $TargetDirectory 'RESTORE_ALL.ps1')
    $manifest = [ordered]@{
        created_at = (Get-Date).ToString('o')
        source_root = $root
        compose_project = 'sunhold-legal-platform'
        services = $services
        exported_volumes = @('postgres_data','minio_data','uploads_data')
        frontend = 'React 19 + TypeScript + Vite + Ant Design'
        backend = 'FastAPI + SQLAlchemy Async + Celery'
        verification = [ordered]@{
            menu_nodes = 265
            menu_leaves = 220
            api_smoke_groups = 17
            docker_services = 6
        }
        security = [ordered]@{
            plaintext_business_data = $true
            archive_encrypted = $false
            postgres_globals_exported = $false
            redis_data_exported = $false
            redis_restore_mode = 'empty_start'
            transfer_requirement = '仅使用组织批准的加密介质或加密通道；ZIP 仅压缩，不提供加密。'
        }
        excluded = @(
            'sfhc（无关且含保密资料）','真实 .env 与除两个安全 example 文件外的 .env.*',
            'backup/backups','node_modules','dist','.venv','__pycache__',
            '密钥和私钥证书容器','日志和临时文件','项目内旧 ZIP','postgres_globals.sql','Redis 持久化数据'
        )
    }
    $manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $TargetDirectory 'migration-manifest.json') -Encoding utf8
    $readmeLines = @(
        '# 系统重构迁移包',
        '',
        '请先阅读 project/docs/新电脑恢复与继续开发.md 和 project/AGENTS.md。',
        '',
        '恢复命令：',
        '',
        "powershell -ExecutionPolicy Bypass -File .\RESTORE_ALL.ps1 -TargetDirectory 'C:\Users\你的用户名\Desktop\系统重构'",
        '',
        '警告：本目录包含明文业务数据库和附件，属于保密资料。ZIP 仅用于压缩，不提供加密。',
        '必须存放在受当前用户保护的本机目录，并仅通过组织批准的加密介质或加密通道传输；禁止公开上传。'
    )
    $readmeLines | Set-Content -LiteralPath (Join-Path $TargetDirectory 'README_先读我.md') -Encoding utf8

    Assert-NoSensitiveFiles -ScanRoot $TargetDirectory -Phase '压缩前'
    $hashLines = Get-ChildItem -LiteralPath $TargetDirectory -Recurse -File |
        Where-Object { $_.Name -ne 'SHA256SUMS.txt' } |
        ForEach-Object {
            $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName
            $relative = $_.FullName.Substring($TargetDirectory.Length + 1)
            "$($hash.Hash)  $relative"
        }
    $hashLines | Set-Content -LiteralPath (Join-Path $TargetDirectory 'SHA256SUMS.txt') -Encoding utf8
    Assert-NoSensitiveFiles -ScanRoot $TargetDirectory -Phase '清单生成后'

    Write-Host '[7/7] 迁移包完成' -ForegroundColor Green
    if ($CreateZip) {
        Compress-Archive -LiteralPath $TargetDirectory -DestinationPath $zipPath -CompressionLevel Fastest
        Assert-ZipHasNoSensitiveFiles -ArchivePath $zipPath
        Write-Host "ZIP：$zipPath" -ForegroundColor Green
    }
    Write-Host "目录：$TargetDirectory" -ForegroundColor Green
}
catch {
    $failure = $_
    Write-Warning "迁移导出失败，正在删除未完成输出：$($failure.Exception.Message)"
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue
    }
    if ($outputCreated -and (Test-Path -LiteralPath $TargetDirectory)) {
        Remove-Item -LiteralPath $TargetDirectory -Recurse -Force -ErrorAction SilentlyContinue
    }
    throw $failure
}
finally {
    if ($postgresId) {
        & docker exec $postgresId rm -f /tmp/legal_platform.dump 2>$null | Out-Null
    }
    if ($locationPushed -and $appStopAttempted -and $originalRunningAppServices.Count -gt 0) {
        Write-Host "恢复导出前运行的服务：$($originalRunningAppServices -join ', ')" -ForegroundColor Yellow
        & docker compose start @originalRunningAppServices | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "迁移结束后未能恢复全部应用服务，请手工运行：docker compose start $($originalRunningAppServices -join ' ')"
        }
    }
    if ($locationPushed) { Pop-Location }
}
