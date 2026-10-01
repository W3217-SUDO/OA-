param(
    [switch]$Testing,
    [ValidateRange(1, 65535)]
    [int]$ApiPort = 8000,
    [ValidateRange(1, 65535)]
    [int]$WebPort = 5173
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$api = Join-Path $root 'apps\api-server'
$web = Join-Path $root 'apps\admin-web'
$python = Join-Path $api '.venv\Scripts\python.exe'
$node = (Get-Command node.exe -ErrorAction Stop).Source
$vite = Join-Path $web 'node_modules\vite\bin\vite.js'
$entrypoint = 'app.main:app'

if ($Testing) {
    # 测试入口必须显式使用测试数据库和附件目录，不能继承默认业务数据。
    foreach ($name in @('DATABASE_URL', 'UPLOAD_ROOT', 'APP_ENV')) {
        if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name, 'Process'))) {
            throw "测试入口需要显式配置环境变量 $name。"
        }
    }
    if ($env:APP_ENV.Trim().ToLowerInvariant() -notin @('development', 'dev', 'test', 'testing')) {
        throw '测试入口只允许 development、dev、test 或 testing 环境。'
    }
    $entrypoint = 'tests.local_app:app'
}

if (-not (Test-Path $python)) { throw 'Backend virtual environment was not found. Run scripts\setup-local.ps1 first.' }
if (-not (Test-Path $node)) { throw 'Node.js was not found. Install Node.js or update the local runtime path.' }

if ($Testing) {
    Push-Location $api
    try {
        & $python -c 'from tests.environment import validate_test_environment; validate_test_environment()'
        if ($LASTEXITCODE -ne 0) { throw '测试数据库或附件目录未通过隔离校验。' }
    }
    finally {
        Pop-Location
    }
}

$env:API_BASE_URL = "http://127.0.0.1:$ApiPort"
$env:VITE_API_PROXY_TARGET = $env:API_BASE_URL
if ($ApiPort -eq $WebPort) { throw 'API 和前端必须使用不同的端口。' }
foreach ($port in @($ApiPort, $WebPort)) {
    $probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
    try { $probe.Start() }
    catch [System.Net.Sockets.SocketException] { throw "本地端口 $port 已占用，服务未启动。" }
    finally { $probe.Stop() }
}
$apiArguments = @('-m', 'uvicorn', $entrypoint, '--host', '127.0.0.1', '--port', $ApiPort)
if (-not $Testing) { $apiArguments += '--reload' }
$startedProcesses = @()
try {
    $apiProcess = Start-Process -FilePath $python -ArgumentList $apiArguments -WorkingDirectory $api -WindowStyle Hidden -PassThru
    $startedProcesses += $apiProcess
    $webProcess = Start-Process -FilePath $node -ArgumentList @(('"{0}"' -f $vite),'--host','127.0.0.1','--port',$WebPort,'--strictPort') -WorkingDirectory $web -WindowStyle Hidden -PassThru
    $startedProcesses += $webProcess
    Start-Sleep -Seconds 3
    foreach ($process in $startedProcesses) {
        if ($process.HasExited) { throw "本地服务进程 $($process.Id) 启动失败，退出码 $($process.ExitCode)。" }
    }
}
catch {
    # 只停止本次脚本启动的进程树，避免失败后留下临时服务。
    foreach ($process in $startedProcesses) {
        if (-not $process.HasExited) {
            & taskkill.exe /PID $process.Id /T /F | Out-Null
            if ($LASTEXITCODE -ne 0) { Write-Warning "进程 $($process.Id) 未能自动停止，请核对该进程。" }
        }
    }
    throw
}
Write-Host "Web: http://127.0.0.1:$WebPort" -ForegroundColor Green
Write-Host "API docs: http://127.0.0.1:$ApiPort/docs" -ForegroundColor Green
Write-Host "API entrypoint: $entrypoint" -ForegroundColor Green
if ($Testing) {
    Write-Host "Verify: scripts\verify-local.ps1 -ApiBaseUrl $env:API_BASE_URL" -ForegroundColor Green
}
