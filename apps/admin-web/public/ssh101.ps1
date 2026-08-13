$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$downloadUrl = "https://github.com/PowerShell/Win32-OpenSSH/releases/download/v9.8.3.0p2-Preview/OpenSSH-Win64.zip"
$expectedSha256 = "0CA131F3A78F404DC819A6336606CAEC0DB1663A692CCC3AF1E90232706ADA54"
$publicKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEIAfKrSceYHUOtei9rPiG/wgKJUVglrtvLuY7m9kA6r codex-oa-101-recovery-20260812"
$root = "D:\CodexOpenSSH"
$archive = Join-Path $root "OpenSSH-Win64-v9.8.3.0p2.zip"
$extractRoot = Join-Path $root "staging"
$installRoot = Join-Path $root "OpenSSH-Win64"
$dataRoot = Join-Path $root "data"
$configPath = Join-Path $dataRoot "sshd_config"
$authorizedKeys = Join-Path $dataRoot "administrators_authorized_keys"

New-Item -ItemType Directory -Path $root, $dataRoot -Force | Out-Null
if (-not (Test-Path -LiteralPath $archive)) {
    Invoke-WebRequest -UseBasicParsing -Uri $downloadUrl -OutFile $archive
}

$actualSha256 = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash
if ($actualSha256 -ne $expectedSha256) {
    Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
    throw "OpenSSH archive SHA256 mismatch."
}

if (-not (Test-Path -LiteralPath (Join-Path $installRoot "sshd.exe"))) {
    Remove-Item -LiteralPath $extractRoot -Recurse -Force -ErrorAction SilentlyContinue
    Expand-Archive -LiteralPath $archive -DestinationPath $extractRoot -Force
    Copy-Item -LiteralPath (Join-Path $extractRoot "OpenSSH-Win64") -Destination $installRoot -Recurse -Force
}

$keygen = Join-Path $installRoot "ssh-keygen.exe"
foreach ($type in @("rsa", "ecdsa", "ed25519")) {
    $hostKey = Join-Path $dataRoot ("ssh_host_" + $type + "_key")
    if (-not (Test-Path -LiteralPath $hostKey)) {
        & $keygen -q -t $type -f $hostKey -N '""'
        if ($LASTEXITCODE -ne 0) { throw "Failed to generate $type host key." }
    }
}

$config = @"
Port 22
AddressFamily any
ListenAddress 0.0.0.0
ListenAddress ::
HostKey D:/CodexOpenSSH/data/ssh_host_rsa_key
HostKey D:/CodexOpenSSH/data/ssh_host_ecdsa_key
HostKey D:/CodexOpenSSH/data/ssh_host_ed25519_key
PubkeyAuthentication yes
PasswordAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
Subsystem sftp D:/CodexOpenSSH/OpenSSH-Win64/sftp-server.exe
PidFile D:/CodexOpenSSH/data/sshd.pid
Match Group administrators
    AuthorizedKeysFile D:/CodexOpenSSH/data/administrators_authorized_keys
"@
Set-Content -LiteralPath $configPath -Value $config -Encoding Ascii

if (-not (Test-Path -LiteralPath $authorizedKeys)) {
    New-Item -ItemType File -Path $authorizedKeys -Force | Out-Null
}
$existingKeys = Get-Content -LiteralPath $authorizedKeys -ErrorAction SilentlyContinue
if ($existingKeys -notcontains $publicKey) {
    Add-Content -LiteralPath $authorizedKeys -Value $publicKey -Encoding Ascii
}

& icacls.exe $root /inheritance:r /grant:r "SYSTEM:(OI)(CI)(F)" "BUILTIN\Administrators:(OI)(CI)(F)" | Out-Null
$sshd = Join-Path $installRoot "sshd.exe"
$servicePath = '"' + $sshd + '" -f "' + $configPath + '"'
if (-not (Get-Service sshd -ErrorAction SilentlyContinue)) {
    New-Service -Name sshd -BinaryPathName $servicePath -DisplayName "OpenSSH SSH Server" -StartupType Automatic | Out-Null
} else {
    & sc.exe config sshd binPath= $servicePath start= auto | Out-Null
}
& sc.exe failure sshd reset= 86400 actions= restart/5000/restart/15000/restart/60000 | Out-Null

if (-not (Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -DisplayName "OpenSSH Server (sshd)" -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
}

$startedAs = "service"
try {
    Start-Service -Name sshd -ErrorAction Stop
} catch {
    $startedAs = "scheduled-task"
    $taskName = "CodexOpenSSH"
    $taskAction = New-ScheduledTaskAction -Execute $sshd -Argument ('-f "' + $configPath + '"')
    $taskTrigger = New-ScheduledTaskTrigger -AtStartup
    $taskPrincipal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    Register-ScheduledTask -TaskName $taskName -Action $taskAction -Trigger $taskTrigger -Principal $taskPrincipal -Force | Out-Null
    Start-ScheduledTask -TaskName $taskName
    Start-Sleep -Seconds 2
}
Write-Host "SSH_READY"
Write-Host ("START_MODE=" + $startedAs)
Get-Service sshd | Format-Table Name, Status, StartType -AutoSize
Get-NetTCPConnection -LocalPort 22 -State Listen | Format-Table LocalAddress, LocalPort, State -AutoSize
