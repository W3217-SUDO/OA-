param(
    [string]$PythonExecutable = 'python.exe',
    [switch]$InstallQualityHook,
    [switch]$QualityHookOnly
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$api = Join-Path $root 'apps\api-server'
$web = Join-Path $root 'apps\admin-web'

function Install-QualityPrePushHook {
    # 只安装本仓库默认 hooks，不改全局配置，也不覆盖用户原有 hook。
    $top = & git -C $root rev-parse --show-toplevel
    if ($LASTEXITCODE -ne 0 -or [IO.Path]::GetFullPath($top.Trim()) -ne [IO.Path]::GetFullPath($root)) {
        throw '无法确认当前项目 Git 根目录，拒绝安装 hook。'
    }
    $null = & git -C $root config --get core.hooksPath
    if ($LASTEXITCODE -notin @(0, 1)) { throw '无法读取 Git hooksPath。' }
    if ($LASTEXITCODE -eq 0) { throw '已有 core.hooksPath 配置，请由其维护者集成 OA pre-push；本脚本不会覆盖。' }
    $hooksDirectory = & git -C $root rev-parse --git-path hooks
    if ($LASTEXITCODE -ne 0) { throw '无法定位当前仓库的 hooks 目录。' }
    if (-not [IO.Path]::IsPathRooted($hooksDirectory)) { $hooksDirectory = Join-Path $root $hooksDirectory }
    if ((Test-Path -LiteralPath $hooksDirectory) -and ((Get-Item -LiteralPath $hooksDirectory).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw '默认 hooks 目录是链接，拒绝修改未知外部目录。'
    }
    $source = Join-Path $root '.githooks\pre-push'
    $destination = Join-Path $hooksDirectory 'pre-push'
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw '缺少仓库 pre-push hook。' }
    $hookContent = [IO.File]::ReadAllText($source, [Text.Encoding]::UTF8).Replace("`r`n", "`n")
    $managedHeader = "#!/bin/sh`n# OA_MANAGED_PRE_PUSH_V1`n"
    if (-not $hookContent.StartsWith($managedHeader, [StringComparison]::Ordinal)) {
        throw '仓库 pre-push 缺少受管理模板标记。'
    }
    $writeHook = $true
    if (Test-Path -LiteralPath $destination) {
        if ((Get-Item -LiteralPath $destination).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw '已有 pre-push 是链接，拒绝覆盖。'
        }
        $installed = [IO.File]::ReadAllText($destination, [Text.Encoding]::UTF8)
        if ($installed -ceq $hookContent) { $writeHook = $false }
        elseif (-not $installed.StartsWith($managedHeader, [StringComparison]::Ordinal)) {
            throw '已有外来 pre-push hook，请由其维护者集成；本脚本不会覆盖。'
        }
    }
    if ($writeHook) {
        [IO.Directory]::CreateDirectory($hooksDirectory) | Out-Null
        # Git 的自动换行可能把仓库文件转为 CRLF；shell hook 必须安装为无 BOM 的 LF。
        [IO.File]::WriteAllText($destination, $hookContent, [Text.UTF8Encoding]::new($false))
    }
    if ($env:OS -ne 'Windows_NT') {
        & chmod +x -- $destination
        if ($LASTEXITCODE -ne 0) { throw '无法设置 pre-push 可执行权限。' }
        & test -x $destination
        if ($LASTEXITCODE -ne 0) { throw 'pre-push 不具备可执行权限。' }
    }
    Write-Host "已安装 OA pre-push：$destination；推送 dev/main 必须设置 OA_QUALITY_PYTHON 与 OA_QUALITY_NODE；OA_QUALITY_JOBS 默认 2。"
}

if ($MyInvocation.InvocationName -eq '.') { return }
if ($QualityHookOnly -and -not $InstallQualityHook) { throw 'QualityHookOnly 必须同时指定 InstallQualityHook。' }
if ($QualityHookOnly) {
    Install-QualityPrePushHook
    return
}

$python = (Get-Command $PythonExecutable -ErrorAction Stop).Source
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source

if (-not (Test-Path $python)) { throw 'Python executable was not found.' }
if (-not (Test-Path $npm)) { throw 'npm was not found.' }
$pythonVersion = & $python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))'
if ($LASTEXITCODE -ne 0 -or $pythonVersion -ne '3.12') { throw '开发环境要求 Python 3.12，请通过 PythonExecutable 指定对应运行时。' }
$nodeVersion = & node --version
if ($LASTEXITCODE -ne 0 -or $nodeVersion -notmatch '^v22\.') { throw '开发环境要求 Node.js 22，请先切换 Node 版本。' }

if (-not (Test-Path (Join-Path $api '.venv'))) {
    & $python -m venv (Join-Path $api '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Backend virtual environment creation failed.' }
}
& (Join-Path $api '.venv\Scripts\python.exe') -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed.' }
& (Join-Path $api '.venv\Scripts\python.exe') -m pip install --require-hashes -r (Join-Path $api 'requirements.lock')
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }
& (Join-Path $api '.venv\Scripts\python.exe') -m pip install --require-hashes -r (Join-Path $root 'requirements-dev.lock')
if ($LASTEXITCODE -ne 0) { throw 'Quality tool dependency installation failed.' }
Push-Location $web
try {
    # 使用锁文件安装，避免不同电脑得到不同的前端依赖版本。
    & $npm ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
}
finally { Pop-Location }
if ($InstallQualityHook) { Install-QualityPrePushHook }
Write-Host 'Local development environment is ready. Run scripts\start-local.ps1.' -ForegroundColor Green
