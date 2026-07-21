$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$api = Join-Path $root 'apps\api-server'
$web = Join-Path $root 'apps\admin-web'
$python = 'C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe'
$npm = 'C:\Users\Administrator\AppData\Local\CodexTools\node\node-v24.18.0-win-x64\npm.cmd'

if (-not (Test-Path $python)) { throw 'Python 3.13 was not found.' }
if (-not (Test-Path $npm)) { throw 'npm was not found.' }

if (-not (Test-Path (Join-Path $api '.venv'))) { & $python -m venv (Join-Path $api '.venv') }
& (Join-Path $api '.venv\Scripts\python.exe') -m pip install --upgrade pip
& (Join-Path $api '.venv\Scripts\python.exe') -m pip install -r (Join-Path $api 'requirements.txt')
Push-Location $web
try { & $npm install } finally { Pop-Location }
Write-Host 'Local development environment is ready. Run scripts\start-local.ps1.' -ForegroundColor Green
