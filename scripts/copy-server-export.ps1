param(
    [Parameter(Mandatory = $true)]
    [string]$RemotePath,

    [Parameter(Mandatory = $true)]
    [string]$LocalPath,

    [string]$Server = "139.224.35.141",
    [string]$CredentialTarget = "TERMSRV/139.224.35.141",
    [string]$UserName = "Administrator"
)

$ErrorActionPreference = "Stop"

Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class NativeCredentialReader
{
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct CREDENTIAL
    {
        public UInt32 Flags;
        public UInt32 Type;
        public string TargetName;
        public string Comment;
        public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
        public UInt32 CredentialBlobSize;
        public IntPtr CredentialBlob;
        public UInt32 Persist;
        public UInt32 AttributeCount;
        public IntPtr Attributes;
        public string TargetAlias;
        public string UserName;
    }

    [DllImport("advapi32.dll", EntryPoint = "CredReadW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool CredRead(string target, int type, int reservedFlag, out IntPtr credentialPtr);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern void CredFree(IntPtr credentialPtr);

    public static string ReadPassword(string target)
    {
        IntPtr credentialPtr;
        if (!CredRead(target, 1, 0, out credentialPtr))
            throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());

        try
        {
            CREDENTIAL credential = (CREDENTIAL)Marshal.PtrToStructure(credentialPtr, typeof(CREDENTIAL));
            return Marshal.PtrToStringUni(credential.CredentialBlob, (int)credential.CredentialBlobSize / 2);
        }
        finally
        {
            CredFree(credentialPtr);
        }
    }
}
"@

$plainTextPassword = [NativeCredentialReader]::ReadPassword($CredentialTarget)
$securePassword = ConvertTo-SecureString $plainTextPassword -AsPlainText -Force
$plainTextPassword = $null
$credential = [PSCredential]::new($UserName, $securePassword)
$driveName = "OAExport" + [Guid]::NewGuid().ToString("N").Substring(0, 8)

try {
    New-PSDrive -Name $driveName -PSProvider FileSystem -Root "\\$Server\G$" -Credential $credential -Scope Script | Out-Null
    $relativePath = $RemotePath -replace '^[Gg]:\\', ''
    $source = "$driveName`:\$relativePath"
    $destinationDirectory = Split-Path -Parent $LocalPath
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $LocalPath -Force
    $file = Get-Item -LiteralPath $LocalPath
    $hash = Get-FileHash -LiteralPath $LocalPath -Algorithm SHA256
    [pscustomobject]@{
        LocalPath = $file.FullName
        Bytes = $file.Length
        SHA256 = $hash.Hash
    } | Format-List
}
finally {
    Remove-PSDrive -Name $driveName -Force -ErrorAction SilentlyContinue
}
