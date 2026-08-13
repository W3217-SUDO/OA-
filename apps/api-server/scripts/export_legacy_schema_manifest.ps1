param(
    [string]$Server = "localhost",
    [string]$Database = "PRD_CRM_GD_20200211",
    [string]$Output = (Join-Path $PSScriptRoot "..\app\legacy_schema_manifest.json")
)

$connection = [System.Data.SqlClient.SqlConnection]::new(
    "Server=$Server;Database=$Database;Integrated Security=true;TrustServerCertificate=true"
)
$connection.Open()
try {
    $columnCommand = $connection.CreateCommand()
    $columnCommand.CommandText = @"
SELECT
    t.name AS table_name,
    c.column_id,
    c.name AS column_name,
    ty.name AS data_type,
    c.max_length,
    c.precision,
    c.scale,
    c.is_nullable,
    c.is_identity,
    CONVERT(bigint, ISNULL(ic.seed_value, 1)) AS identity_seed,
    CONVERT(bigint, ISNULL(ic.increment_value, 1)) AS identity_increment,
    ISNULL(pk.key_ordinal, 0) AS primary_key_ordinal
FROM sys.tables t
JOIN sys.schemas s ON s.schema_id = t.schema_id
JOIN sys.columns c ON c.object_id = t.object_id
JOIN sys.types ty ON ty.user_type_id = c.user_type_id
LEFT JOIN sys.identity_columns ic
    ON ic.object_id = c.object_id AND ic.column_id = c.column_id
LEFT JOIN (
    SELECT ix.object_id, ixc.column_id, ixc.key_ordinal
    FROM sys.indexes ix
    JOIN sys.index_columns ixc
        ON ixc.object_id = ix.object_id AND ixc.index_id = ix.index_id
    WHERE ix.is_primary_key = 1
) pk ON pk.object_id = c.object_id AND pk.column_id = c.column_id
WHERE s.name = 'dbo'
ORDER BY t.name, c.column_id
"@
    $columns = [System.Data.DataTable]::new()
    $columns.Load($columnCommand.ExecuteReader())

    $indexCommand = $connection.CreateCommand()
    $indexCommand.CommandText = @"
SELECT
    t.name AS table_name,
    ix.name AS index_name,
    ix.is_unique,
    ic.index_column_id,
    c.name AS column_name,
    ic.is_descending_key,
    ic.is_included_column
FROM sys.tables t
JOIN sys.schemas s ON s.schema_id = t.schema_id
JOIN sys.indexes ix ON ix.object_id = t.object_id
JOIN sys.index_columns ic
    ON ic.object_id = ix.object_id AND ic.index_id = ix.index_id
JOIN sys.columns c
    ON c.object_id = ic.object_id AND c.column_id = ic.column_id
WHERE s.name = 'dbo'
  AND ix.index_id > 0
  AND ix.is_hypothetical = 0
  AND ix.is_primary_key = 0
ORDER BY t.name, ix.name, ic.index_column_id
"@
    $indexes = [System.Data.DataTable]::new()
    $indexes.Load($indexCommand.ExecuteReader())

    $tables = @()
    foreach ($tableGroup in ($columns | Group-Object table_name)) {
        $tableName = $tableGroup.Name
        $tableIndexes = @()
        foreach ($indexGroup in ($indexes | Where-Object table_name -eq $tableName | Group-Object index_name)) {
            $first = $indexGroup.Group[0]
            $tableIndexes += [ordered]@{
                name = [string]$indexGroup.Name
                unique = [bool]$first.is_unique
                columns = @($indexGroup.Group | ForEach-Object {
                    [ordered]@{
                        name = [string]$_.column_name
                        descending = [bool]$_.is_descending_key
                        included = [bool]$_.is_included_column
                    }
                })
            }
        }
        $tables += [ordered]@{
            name = [string]$tableName
            columns = @($tableGroup.Group | ForEach-Object {
                [ordered]@{
                    name = [string]$_.column_name
                    type = [string]$_.data_type
                    max_length = [int]$_.max_length
                    precision = [int]$_.precision
                    scale = [int]$_.scale
                    nullable = [bool]$_.is_nullable
                    identity = [bool]$_.is_identity
                    identity_seed = [long]$_.identity_seed
                    identity_increment = [long]$_.identity_increment
                    primary_key_ordinal = [int]$_.primary_key_ordinal
                }
            })
            indexes = $tableIndexes
        }
    }
    $manifest = [ordered]@{
        source = [ordered]@{ server = $Server; database = $Database; schema = "dbo" }
        table_count = $tables.Count
        tables = $tables
    }
    $json = $manifest | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText((Resolve-Path (Split-Path $Output)).Path + "\" + (Split-Path $Output -Leaf), $json + "`n", [System.Text.UTF8Encoding]::new($false))
    Write-Output "Exported $($tables.Count) tables to $Output"
}
finally {
    $connection.Dispose()
}
