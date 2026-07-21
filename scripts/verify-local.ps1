$ErrorActionPreference = 'Stop'
$utf8 = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
$env:PYTHONIOENCODING = 'utf-8'

$root = Split-Path -Parent $PSScriptRoot
$web = Join-Path $root 'apps\admin-web'
$python = Join-Path $root 'apps\api-server\.venv\Scripts\python.exe'

$localEnv = Join-Path $root '.env'
if (Test-Path -LiteralPath $localEnv) {
    foreach ($line in Get-Content -LiteralPath $localEnv -Encoding UTF8) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#') -or -not $trimmed.Contains('=')) { continue }
        $parts = $trimmed.Split('=', 2)
        # Windows CRT does not understand IANA names such as Asia/Shanghai and
        # may silently switch Python's local date to UTC around midnight.
        # Compose still reads TZ directly from .env for Linux containers.
        if ($parts[0] -eq 'TZ' -and [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT) { continue }
        if (-not [Environment]::GetEnvironmentVariable($parts[0], 'Process')) {
            [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
        }
    }
}

if (-not (Test-Path -LiteralPath $python)) {
    throw 'Python virtual environment is missing. Run scripts\setup-local.ps1 first.'
}

if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    $nodeHome = Get-ChildItem -LiteralPath (Join-Path $env:LOCALAPPDATA 'CodexTools\node') -Directory -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending |
        Select-Object -First 1
    if (-not $nodeHome) {
        throw 'Node.js was not found. Run scripts\setup-local.ps1 first.'
    }
    $env:Path = "$($nodeHome.FullName);$env:Path"
}

Write-Host '[1/5] Frontend production build' -ForegroundColor Cyan
Push-Location $web
try {
    # Run the local binaries directly. npm on Node 24 for Windows can finish the
    # Vite build successfully and then abort in libuv while closing its child
    # process, which produces a false-negative verification result.
    & (Join-Path $web 'node_modules\.bin\tsc.cmd') -b
    if ($LASTEXITCODE -ne 0) { throw 'Frontend TypeScript build failed.' }
    & (Join-Path $web 'node_modules\.bin\vite.cmd') build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend Vite production build failed.' }
}
finally {
    Pop-Location
}

Write-Host '[2/5] Python compile check' -ForegroundColor Cyan
& $python -m compileall -q (Join-Path $root 'apps\api-server\app') (Join-Path $root 'scripts\smoke-api.py') (Join-Path $root 'scripts\audit-menu-coverage.py') (Join-Path $root 'scripts\audit-client-api-coverage.py')
if ($LASTEXITCODE -ne 0) { throw 'Python compile check failed.' }

Write-Host '[3/5] Menu and page structural coverage' -ForegroundColor Cyan
& $python (Join-Path $root 'scripts\audit-menu-coverage.py')
if ($LASTEXITCODE -ne 0) { throw 'Menu and page coverage verification failed.' }
& $python (Join-Path $root 'scripts\audit-client-api-coverage.py')
if ($LASTEXITCODE -ne 0) { throw 'Frontend API route coverage verification failed.' }

Write-Host '[4/5] API end-to-end business flows' -ForegroundColor Cyan
& $python (Join-Path $root 'scripts\smoke-api.py')
if ($LASTEXITCODE -ne 0) { throw 'API end-to-end verification failed.' }

Write-Host '[5/5] Docker Compose configuration' -ForegroundColor Cyan
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Push-Location $root
    try {
        & docker compose config --quiet
        if ($LASTEXITCODE -ne 0) { throw 'Docker Compose configuration is invalid.' }
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host 'Docker command was not found; skipping Compose validation.' -ForegroundColor Yellow
}

Write-Host 'VERIFY_LOCAL_OK: frontend, API flows, and deployment configuration passed.' -ForegroundColor Green
