param(
    [string]$ApiBase = "http://150.158.3.104:8089/api/v1",
    [string]$SerialNo = "RW2413300774776",
    [string]$BearerToken = $env:OA_ROW18_READONLY_TOKEN,
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($BearerToken)) {
    throw "Set OA_ROW18_READONLY_TOKEN to an existing read-only session token."
}

$headers = @{ Authorization = "Bearer $BearerToken" }
function Invoke-ReadOnlyGet([string]$Path, [hashtable]$Query = @{}) {
    $builder = [UriBuilder]::new("$($ApiBase.TrimEnd('/'))/$($Path.TrimStart('/'))")
    if ($Query.Count) {
        $builder.Query = ($Query.GetEnumerator() | ForEach-Object {
            "{0}={1}" -f [Uri]::EscapeDataString([string]$_.Key), [Uri]::EscapeDataString([string]$_.Value)
        }) -join "&"
    }
    Invoke-RestMethod -Method Get -Uri $builder.Uri.AbsoluteUri -Headers $headers
}

$search = Invoke-ReadOnlyGet "/records" @{ module = "investigation"; keyword = $SerialNo; page_size = 100 }
$matches = @($search.items | Where-Object { $_.serial_no -eq $SerialNo })
if ($matches.Count -ne 1) { throw "Expected one exact investigation $SerialNo, found $($matches.Count)." }
$record = Invoke-ReadOnlyGet "/records/$($matches[0].id)"
$tasks = Invoke-ReadOnlyGet "/investigations/$($matches[0].id)/tasks"
$data = $record.data
$contractNo = [string]($data.contract_no)
$contracts = if ($contractNo) {
    Invoke-ReadOnlyGet "/records" @{ module = "contract"; keyword = $contractNo; page_size = 100 }
} else { @{ items = @(); total = 0 } }

$payload = [ordered]@{
    schema = "oa-row18-readonly-export-v1"
    exported_at = (Get-Date).ToUniversalTime().ToString("o")
    api_base = $ApiBase
    http_methods = @("GET")
    serial_no = $SerialNo
    investigation = $record
    tasks = $tasks
    contracts = $contracts
    people = @($record.owner, $data.source_owner, $data.assigner, $data.assigned_by) |
        Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | Select-Object -Unique
}
$resolved = [IO.Path]::GetFullPath($OutputPath)
[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($resolved)) | Out-Null
$payload | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $resolved -Encoding UTF8
[pscustomobject]@{ Output = $resolved; InvestigationId = $matches[0].id; TaskCount = @($tasks.items).Count; ContractCount = @($contracts.items).Count } | ConvertTo-Json -Compress
