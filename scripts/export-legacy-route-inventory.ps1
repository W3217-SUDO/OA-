param(
    [string]$LegacySourceRoot = "",
    [string]$OutputDirectory = (Join-Path $PSScriptRoot "..\artifacts")
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
if ([string]::IsNullOrWhiteSpace($LegacySourceRoot)) {
    $workspaceRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
    $LegacySourceRoot = Join-Path $workspaceRoot "legacy-gdcrm-101-local-20260812\source\GD.CRM.WEB"
}

$sourceFiles = @(rg --files $LegacySourceRoot)
$controllers = $sourceFiles | Where-Object { $_ -like '*Controller.cs' } |
    ForEach-Object {
        $fullPath = if ([System.IO.Path]::IsPathRooted($_)) { $_ } else { Join-Path $LegacySourceRoot $_ }
        $relative = $fullPath.Substring($LegacySourceRoot.Length).TrimStart('\')
        $file = Get-Item -LiteralPath $fullPath
        [pscustomobject]@{
            controller_path = $relative
            area = if ($relative -match '^Areas\\([^\\]+)') { $Matches[1] } else { '' }
            controller = $file.BaseName -replace 'Controller$', ''
            source_bytes = $file.Length
        }
    } |
    Sort-Object area, controller, controller_path

$views = $sourceFiles | Where-Object { $_ -like '*.cshtml' } |
    ForEach-Object {
        $fullPath = if ([System.IO.Path]::IsPathRooted($_)) { $_ } else { Join-Path $LegacySourceRoot $_ }
        $relative = $fullPath.Substring($LegacySourceRoot.Length).TrimStart('\')
        $file = Get-Item -LiteralPath $fullPath
        [pscustomobject]@{
            view_path = $relative
            area = if ($relative -match '^Areas\\([^\\]+)') { $Matches[1] } else { '' }
            source_bytes = $file.Length
        }
    } |
    Sort-Object area, view_path

$controllers | Export-Csv (Join-Path $OutputDirectory "legacy-controllers.csv") -NoTypeInformation -Encoding UTF8
$views | Export-Csv (Join-Path $OutputDirectory "legacy-views.csv") -NoTypeInformation -Encoding UTF8

[ordered]@{
    exported_at = (Get-Date).ToString("o")
    source_root = $LegacySourceRoot
    controllers = $controllers.Count
    views = $views.Count
    areas = ($controllers.area | Where-Object { $_ } | Select-Object -Unique).Count
} | ConvertTo-Json | Set-Content (Join-Path $OutputDirectory "route-inventory-summary.json") -Encoding UTF8
