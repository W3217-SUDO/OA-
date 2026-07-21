$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$api = Join-Path $root 'apps\api-server'
$web = Join-Path $root 'apps\admin-web'
$python = Join-Path $api '.venv\Scripts\python.exe'
$node = 'C:\Users\Administrator\AppData\Local\CodexTools\node\node-v24.18.0-win-x64\node.exe'
$vite = Join-Path $web 'node_modules\vite\bin\vite.js'

if (-not (Test-Path $python)) { throw 'Backend virtual environment was not found. Run scripts\setup-local.ps1 first.' }
if (-not (Test-Path $node)) { throw 'Node.js was not found at the expected path.' }

Start-Process -FilePath $python -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000','--reload') -WorkingDirectory $api -WindowStyle Hidden
Start-Process -FilePath $node -ArgumentList @($vite,'--host','127.0.0.1') -WorkingDirectory $web -WindowStyle Hidden
Start-Sleep -Seconds 3
Write-Host 'Web: http://127.0.0.1:5173' -ForegroundColor Green
Write-Host 'API docs: http://127.0.0.1:8000/docs' -ForegroundColor Green
