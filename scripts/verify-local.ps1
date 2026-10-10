param(
    [string]$Python = '',
    [string]$Node = 'node',
    [string]$ReportDirectory = '',
    [ValidateSet('full', 'static', 'source')][string]$Profile = 'full',
    [int]$Jobs = 2
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $Python) { $Python = Join-Path $root 'apps\api-server\.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $Python)) { throw '请先运行 setup-local.ps1，或用 -Python 指定 Python 3.12 环境。' }
if (-not $ReportDirectory) {
    $ReportDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ('oa-quality-' + [guid]::NewGuid().ToString('N'))
}
# 门禁自行创建隔离数据库和附件目录，不加载可能指向生产的 .env。
& $Python (Join-Path $PSScriptRoot 'quality_gate.py') --node $Node --report-dir $ReportDirectory --profile $Profile --jobs $Jobs
if ($LASTEXITCODE -ne 0) { throw "质量检查未通过，请查看：$ReportDirectory" }
Write-Host "质量检查通过，检查范围：$Profile；报告：$ReportDirectory"
