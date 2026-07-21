$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1

Write-Host "CPU: $($cpu.Name)"
Write-Host "Firmware virtualization: $($cpu.VirtualizationFirmwareEnabled)"

if (-not $cpu.VirtualizationFirmwareEnabled) {
    Write-Host 'Firmware virtualization is disabled. Reboot into BIOS/UEFI, enable SVM Mode (AMD) or Intel Virtualization Technology, save, and reboot Windows.' -ForegroundColor Red
    exit 2
}

$requiredFeatures = @(
    'Microsoft-Windows-Subsystem-Linux',
    'VirtualMachinePlatform',
    'Microsoft-Hyper-V-All'
)

foreach ($featureName in $requiredFeatures) {
    $feature = Get-WindowsOptionalFeature -Online -FeatureName $featureName
    Write-Host "$featureName`: $($feature.State)"
    if ($feature.State -ne 'Enabled') {
        Write-Host "$featureName is not enabled. Enable it and reboot Windows." -ForegroundColor Red
        exit 3
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host 'Docker command was not found. Install or repair Docker Desktop.' -ForegroundColor Red
    exit 4
}

Push-Location $root
try {
    & docker compose config --quiet
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Compose configuration is invalid.'
    }
}
finally {
    Pop-Location
}

Write-Host 'DOCKER_PREFLIGHT_OK' -ForegroundColor Green
