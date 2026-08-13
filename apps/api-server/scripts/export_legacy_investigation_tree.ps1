param(
    [string]$Server = "localhost",
    [string]$Database = "PRD_CRM_GD_20200211",
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"
$connectionString = "Server=$Server;Database=$Database;Integrated Security=true;TrustServerCertificate=true;ApplicationIntent=ReadOnly"
$connection = [Data.SqlClient.SqlConnection]::new($connectionString)
$connection.Open()
try {
    $dataSet = [Data.DataSet]::new("LegacyInvestigationTree")
    $queries = [ordered]@{
        Legal_Investigation = @"
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
SELECT * FROM dbo.Legal_Investigation ORDER BY InvestigationId;
"@
        Legal_Investigation_Task = @"
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
SELECT * FROM dbo.Legal_Investigation_Task ORDER BY TaskId;
"@
        HR_Staff = @"
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
WITH people AS (
    SELECT Investigator UserName FROM dbo.Legal_Investigation_Task
    UNION SELECT Assistant FROM dbo.Legal_Investigation_Task
    UNION SELECT CreateUser FROM dbo.Legal_Investigation_Task
    UNION SELECT ChangeUser FROM dbo.Legal_Investigation_Task
    UNION SELECT BusinessOwner FROM dbo.Legal_Investigation
    UNION SELECT Auditor FROM dbo.Legal_Investigation
    UNION SELECT CreateUser FROM dbo.Legal_Investigation
    UNION SELECT ChangeUser FROM dbo.Legal_Investigation
)
SELECT DISTINCT
    s.StaffNo,
    s.StaffName,
    s.StaffChName,
    s.DepartmentId,
    d.DepartmentName,
    s.IsActived
FROM dbo.HR_Staff s
JOIN people p ON p.UserName = s.StaffName
LEFT JOIN dbo.HR_Department d ON d.DepartmentId = s.DepartmentId
WHERE NULLIF(p.UserName, '') IS NOT NULL
ORDER BY s.StaffName;
"@
    }

    foreach ($entry in $queries.GetEnumerator()) {
        $command = $connection.CreateCommand()
        $command.CommandTimeout = 300
        $command.CommandText = $entry.Value
        $adapter = [Data.SqlClient.SqlDataAdapter]::new($command)
        $table = [Data.DataTable]::new($entry.Key)
        [void]$adapter.Fill($table)
        [void]$dataSet.Tables.Add($table)
    }

    $resolvedOutput = [IO.Path]::GetFullPath($OutputPath)
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($resolvedOutput)) | Out-Null
    $memory = [IO.MemoryStream]::new()
    $gzip = [IO.Compression.GZipStream]::new($memory, [IO.Compression.CompressionMode]::Compress, $true)
    $dataSet.WriteXml($gzip, [Data.XmlWriteMode]::WriteSchema)
    $gzip.Dispose()
    [IO.File]::WriteAllText($resolvedOutput, [Convert]::ToBase64String($memory.ToArray()), [Text.Encoding]::ASCII)

    [pscustomobject]@{
        Output = $resolvedOutput
        Investigations = $dataSet.Tables["Legal_Investigation"].Rows.Count
        Tasks = $dataSet.Tables["Legal_Investigation_Task"].Rows.Count
        Staff = $dataSet.Tables["HR_Staff"].Rows.Count
    } | ConvertTo-Json -Compress
}
finally {
    $connection.Close()
}
