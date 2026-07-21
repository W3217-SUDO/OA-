param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$TargetDirectory,
    [switch]$CreateZip
)

$ErrorActionPreference = 'Stop'
$sourceRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$TargetDirectory = [System.IO.Path]::GetFullPath($TargetDirectory)
$zipPath = "$TargetDirectory.zip"
$outputCreated = $false

function Test-SensitiveDeliveryPath {
    param([Parameter(Mandatory = $true)][string]$RelativePath)

    $normalized = $RelativePath.Replace('/', '\').TrimStart('\')
    $segments = @($normalized -split '\\' | Where-Object { $_ })
    if ($segments.Count -eq 0) { return $false }

    $blockedDirectories = @(
        '.git', 'sfhc', 'data', 'backup', 'backups', 'uploads',
        'node_modules', 'dist', '.venv', '__pycache__',
        '.cache', '.pytest_cache', '.mypy_cache', '.ruff_cache',
        'cache', 'log', 'logs', 'tmp', 'temp'
    )
    foreach ($segment in $segments) {
        if ($blockedDirectories -contains $segment.ToLowerInvariant()) { return $true }
    }

    $leaf = $segments[-1].ToLowerInvariant()
    if ($leaf -eq '.env.example' -or $leaf -eq '.env.production.example') { return $false }
    if ($leaf -eq '.env' -or $leaf.StartsWith('.env.')) { return $true }
    if ($leaf -match '\.(db|sqlite|sqlite3)$') { return $true }
    if ($leaf -eq 'postgres_globals.sql') { return $true }
    if ($leaf -match '^(id_rsa|id_ed25519)(\.|$)') { return $true }
    if ($leaf -match '\.(key|pem|p12|pfx|ppk|jks|keystore|kdbx)$') { return $true }
    if ($leaf -match '\.(log|tmp|temp|bak|old|swp|swo|dmp|dump|pyc|pyo|zip|tar)$') { return $true }
    if ($leaf -match '\.(sql|dump)\.(gz|bz2|xz)$') { return $true }
    return $false
}

function Assert-NoSensitiveDeliveryPaths {
    param(
        [Parameter(Mandatory = $true)][string]$ScanRoot,
        [Parameter(Mandatory = $true)][string]$Phase
    )

    $hits = @()
    foreach ($item in Get-ChildItem -LiteralPath $ScanRoot -Recurse -Force) {
        $relative = $item.FullName.Substring($ScanRoot.Length).TrimStart('\')
        if (Test-SensitiveDeliveryPath -RelativePath $relative) {
            $hits += $relative
            if ($hits.Count -ge 20) { break }
        }
    }
    if ($hits.Count -gt 0) {
        throw "$Phase 敏感文件名扫描失败：$($hits -join '; ')"
    }
}

function Assert-ZipHasNoSensitiveDeliveryPaths {
    param([Parameter(Mandatory = $true)][string]$ArchivePath)

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($ArchivePath)
    try {
        $hits = @()
        foreach ($entry in $archive.Entries) {
            if (Test-SensitiveDeliveryPath -RelativePath $entry.FullName) {
                $hits += $entry.FullName
                if ($hits.Count -ge 20) { break }
            }
        }
        if ($hits.Count -gt 0) {
            throw "ZIP 条目敏感文件名扫描失败：$($hits -join '; ')"
        }
    }
    finally {
        $archive.Dispose()
    }
}

if (-not [System.IO.Path]::IsPathRooted($TargetDirectory) -or $TargetDirectory.StartsWith('\\')) {
    throw '必须指定本机磁盘上的绝对目标目录。'
}
$sourcePrefix = $sourceRoot.TrimEnd('\') + '\'
if ($TargetDirectory.Equals($sourceRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
    $TargetDirectory.StartsWith($sourcePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw '交付目录不能位于源码目录内。'
}
if (Test-Path -LiteralPath $TargetDirectory) { throw "目标目录已存在：$TargetDirectory" }
if (Test-Path -LiteralPath $zipPath) { throw "目标 ZIP 已存在：$zipPath" }

try {
    New-Item -ItemType Directory -Path $TargetDirectory -Force | Out-Null
    $outputCreated = $true

    $excludeDirs = @(
        '.git','sfhc','data','backup','backups','uploads',
        'node_modules','dist','.venv','__pycache__',
        '.cache','.pytest_cache','.mypy_cache','.ruff_cache',
        'cache','log','logs','tmp','temp'
    )
    $excludeFiles = @(
        '.env','.env.*','postgres_globals.sql',
        '*.pyc','*.pyo','*.log','*.tmp','*.temp','*.bak','*.old','*.swp','*.swo','*.dmp',
        '*.dump','*.sql.gz','*.sql.bz2','*.sql.xz','*.db','*.sqlite','*.sqlite3','*.zip','*.tar',
        '*.key','*.pem','*.p12','*.pfx','*.ppk','*.jks','*.keystore','*.kdbx',
        'id_rsa','id_rsa.*','id_ed25519','id_ed25519.*'
    )

    Write-Host '[1/5] 复制限定范围的源码、文档和部署文件' -ForegroundColor Cyan
    foreach ($directory in @('apps','docs','deploy','scripts')) {
        $source = Join-Path $sourceRoot $directory
        $destination = Join-Path $TargetDirectory $directory
        if (-not (Test-Path -LiteralPath $source -PathType Container)) { throw "缺少交付目录：$directory" }
        & robocopy $source $destination /E /COPY:DAT /DCOPY:DAT /R:2 /W:1 /XD $excludeDirs /XF $excludeFiles /NFL /NDL /NJH /NJS /NP
        if ($LASTEXITCODE -gt 7) { throw "复制 $directory 失败，robocopy=$LASTEXITCODE" }
    }

    foreach ($file in @('AGENTS.md','README.md','.gitignore','docker-compose.yml','compose.prod.yml','compose.test-server.yml')) {
        $source = Join-Path $sourceRoot $file
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "缺少交付文件：$file" }
        Copy-Item -LiteralPath $source -Destination (Join-Path $TargetDirectory $file)
    }
    foreach ($safeEnvExample in @('.env.example','.env.production.example')) {
        $source = Join-Path $sourceRoot $safeEnvExample
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "必须包含安全环境示例：$safeEnvExample" }
        Copy-Item -LiteralPath $source -Destination (Join-Path $TargetDirectory $safeEnvExample)
    }
    Assert-NoSensitiveDeliveryPaths -ScanRoot $TargetDirectory -Phase '复制后'

    Write-Host '[2/5] 生成交付说明' -ForegroundColor Cyan
    $manifestLines = @(
        '# 明日交付候选版源码清单',
        '',
        "- 构建日期：$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss zzz'))",
        '- API 冒烟测试：18 groups',
        '- 菜单覆盖：263 nodes / 218 leaves / 0 unhandled',
        '- 范围：源码、文档、部署配置、Compose 配置、两个安全环境示例和锁文件。',
        '- 安全说明：不包含真实环境变量、运行数据、备份、数据库导出、Docker 镜像、缓存日志或私钥。',
        '',
        '## 完成度声明',
        '',
        '**本候选版不代表生产上线已经完成。** 仍需完成生产数据迁移、逐角色业主验收、短信服务商实发、性能与安全验收。',
        '',
        '## 验收命令',
        '',
        '```powershell',
        'powershell -ExecutionPolicy Bypass -File .\scripts\verify-delivery.ps1',
        '```',
        '',
        '哈希文件 `SHA256SUMS.txt` 覆盖包内除其自身外的所有文件。'
    )
    $manifestLines | Set-Content -LiteralPath (Join-Path $TargetDirectory 'DELIVERY-MANIFEST.md') -Encoding UTF8

    Write-Host '[3/5] 生成并验证 SHA256 清单' -ForegroundColor Cyan
    $hashPath = Join-Path $TargetDirectory 'SHA256SUMS.txt'
    $hashLines = Get-ChildItem -LiteralPath $TargetDirectory -Recurse -File |
        Where-Object { $_.FullName -ne $hashPath } |
        Sort-Object FullName |
        ForEach-Object {
            $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName
            $relative = $_.FullName.Substring($TargetDirectory.Length + 1)
            "$($hash.Hash)  $relative"
        }
    $hashLines | Set-Content -LiteralPath $hashPath -Encoding UTF8
    foreach ($line in Get-Content -LiteralPath $hashPath -Encoding UTF8) {
        if (-not $line.Trim()) { continue }
        $parts = $line -split '  ', 2
        $file = Join-Path $TargetDirectory $parts[1]
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "哈希清单缺少文件：$($parts[1])" }
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $file).Hash -ne $parts[0]) { throw "SHA256 校验失败：$($parts[1])" }
    }
    Assert-NoSensitiveDeliveryPaths -ScanRoot $TargetDirectory -Phase '压缩前'

    Write-Host '[4/5] 创建候选 ZIP' -ForegroundColor Cyan
    if ($CreateZip) {
        Compress-Archive -LiteralPath $TargetDirectory -DestinationPath $zipPath -CompressionLevel Optimal
        Assert-ZipHasNoSensitiveDeliveryPaths -ArchivePath $zipPath
    }

    Write-Host '[5/5] 源码交付候选包完成' -ForegroundColor Green
    Write-Host "目录：$TargetDirectory" -ForegroundColor Green
    if ($CreateZip) { Write-Host "ZIP：$zipPath" -ForegroundColor Green }
}
catch {
    $failure = $_
    Write-Warning "源码交付导出失败，正在删除未完成输出：$($failure.Exception.Message)"
    if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue }
    if ($outputCreated -and (Test-Path -LiteralPath $TargetDirectory)) {
        Remove-Item -LiteralPath $TargetDirectory -Recurse -Force -ErrorAction SilentlyContinue
    }
    throw $failure
}
