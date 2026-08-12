param(
    [string]$Server = "localhost",
    [string]$Database = "PRD_CRM_GD_20200211",
    [string]$OutputDirectory = (Join-Path $PSScriptRoot "..\artifacts")
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$connectionString = "Server=$Server;Database=$Database;Integrated Security=True;TrustServerCertificate=True"
$connection = [System.Data.SqlClient.SqlConnection]::new($connectionString)

function Invoke-LegacyQuery {
    param([Parameter(Mandatory = $true)][string]$Sql)

    $command = $connection.CreateCommand()
    $command.CommandText = $Sql
    $command.CommandTimeout = 300
    $adapter = [System.Data.SqlClient.SqlDataAdapter]::new($command)
    $table = [System.Data.DataTable]::new()
    [void]$adapter.Fill($table)
    return $table
}

try {
    $connection.Open()

    $tables = Invoke-LegacyQuery @"
SELECT
    s.name AS schema_name,
    t.name AS table_name,
    SUM(CASE WHEN p.index_id IN (0, 1) THEN p.rows ELSE 0 END) AS row_count
FROM sys.tables t
JOIN sys.schemas s ON s.schema_id = t.schema_id
LEFT JOIN sys.partitions p ON p.object_id = t.object_id
GROUP BY s.name, t.name
ORDER BY s.name, t.name;
"@

    $columns = Invoke-LegacyQuery @"
SELECT
    s.name AS schema_name,
    t.name AS table_name,
    c.column_id,
    c.name AS column_name,
    ty.name AS data_type,
    c.max_length,
    c.precision,
    c.scale,
    c.is_nullable,
    c.is_identity,
    dc.definition AS default_definition,
    cc.definition AS computed_definition
FROM sys.tables t
JOIN sys.schemas s ON s.schema_id = t.schema_id
JOIN sys.columns c ON c.object_id = t.object_id
JOIN sys.types ty ON ty.user_type_id = c.user_type_id
LEFT JOIN sys.default_constraints dc ON dc.object_id = c.default_object_id
LEFT JOIN sys.computed_columns cc
    ON cc.object_id = c.object_id AND cc.column_id = c.column_id
ORDER BY s.name, t.name, c.column_id;
"@

    $indexes = Invoke-LegacyQuery @"
SELECT
    s.name AS schema_name,
    t.name AS table_name,
    i.name AS index_name,
    i.is_unique,
    i.is_primary_key,
    i.type_desc,
    ic.key_ordinal,
    ic.is_included_column,
    c.name AS column_name
FROM sys.indexes i
JOIN sys.tables t ON t.object_id = i.object_id
JOIN sys.schemas s ON s.schema_id = t.schema_id
JOIN sys.index_columns ic
    ON ic.object_id = i.object_id AND ic.index_id = i.index_id
JOIN sys.columns c
    ON c.object_id = ic.object_id AND c.column_id = ic.column_id
WHERE i.index_id > 0
ORDER BY s.name, t.name, i.name, ic.key_ordinal, c.column_id;
"@

    $foreignKeys = Invoke-LegacyQuery @"
SELECT
    fk.name AS foreign_key_name,
    OBJECT_SCHEMA_NAME(fk.parent_object_id) AS parent_schema,
    OBJECT_NAME(fk.parent_object_id) AS parent_table,
    pc.name AS parent_column,
    OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS referenced_schema,
    OBJECT_NAME(fk.referenced_object_id) AS referenced_table,
    rc.name AS referenced_column
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
JOIN sys.columns pc
    ON pc.object_id = fkc.parent_object_id AND pc.column_id = fkc.parent_column_id
JOIN sys.columns rc
    ON rc.object_id = fkc.referenced_object_id AND rc.column_id = fkc.referenced_column_id
ORDER BY fk.name, fkc.constraint_column_id;
"@

    $modules = Invoke-LegacyQuery @"
SELECT
    o.type_desc,
    s.name AS schema_name,
    o.name AS object_name,
    m.definition
FROM sys.sql_modules m
JOIN sys.objects o ON o.object_id = m.object_id
JOIN sys.schemas s ON s.schema_id = o.schema_id
WHERE o.type IN ('P', 'TR', 'V', 'FN', 'IF', 'TF')
ORDER BY o.type_desc, s.name, o.name;
"@

    $tables | Export-Csv (Join-Path $OutputDirectory "tables.csv") -NoTypeInformation -Encoding UTF8
    $columns | Export-Csv (Join-Path $OutputDirectory "columns.csv") -NoTypeInformation -Encoding UTF8
    $indexes | Export-Csv (Join-Path $OutputDirectory "indexes.csv") -NoTypeInformation -Encoding UTF8
    $foreignKeys | Export-Csv (Join-Path $OutputDirectory "foreign-keys.csv") -NoTypeInformation -Encoding UTF8
    $modules | Export-Csv (Join-Path $OutputDirectory "sql-modules.csv") -NoTypeInformation -Encoding UTF8

    $summary = [ordered]@{
        exported_at = (Get-Date).ToString("o")
        server = $Server
        database = $Database
        tables = $tables.Rows.Count
        columns = $columns.Rows.Count
        indexes = ($indexes | Select-Object index_name -Unique).Count
        foreign_keys = ($foreignKeys | Select-Object foreign_key_name -Unique).Count
        sql_modules = $modules.Rows.Count
        total_rows = [long](($tables | Measure-Object row_count -Sum).Sum)
    }
    $summary | ConvertTo-Json | Set-Content (Join-Path $OutputDirectory "summary.json") -Encoding UTF8
    $summary
}
finally {
    $connection.Close()
}
