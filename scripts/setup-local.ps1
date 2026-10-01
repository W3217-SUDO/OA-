param([string]$PythonExecutable = 'python.exe')

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$api = Join-Path $root 'apps\api-server'
$web = Join-Path $root 'apps\admin-web'
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
Write-Host 'Local development environment is ready. Run scripts\start-local.ps1.' -ForegroundColor Green
