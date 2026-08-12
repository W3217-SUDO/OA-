param(
    [string]$Server = "localhost",
    [string]$Database = "PRD_CRM_GD_20200211",
    [string]$OutputDirectory = (Join-Path $PSScriptRoot "..\artifacts")
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$connection = [System.Data.SqlClient.SqlConnection]::new(
    "Server=$Server;Database=$Database;Integrated Security=True;TrustServerCertificate=True"
)

function Get-DataTable {
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
    $menus = Get-DataTable @"
SELECT MenuId, MenuCode, MenuName, ParentMenuId, OrderId, ImageUrl, LinkUrl,
       Comments, MenuTypeId, IsActived
FROM dbo.SYS_Menu
ORDER BY ParentMenuId, OrderId, MenuId;
"@
    $roles = Get-DataTable @"
SELECT RoleId, CompanyId, RoleName, RoleDesc, CreateUser, CreateTime,
       ChangeUser, ChangeTime
FROM dbo.HR_Role
ORDER BY RoleId;
"@
    $permissions = Get-DataTable @"
SELECT RoleId, ResourceId, ResourceCode, ResourceType, ResourceName,
       CreateUser, CreateTime, ChangeUser, ChangeTime
FROM dbo.HR_Role_Permissions
ORDER BY RoleId, ResourceType, ResourceCode, ResourceId;
"@
    $staff = Get-DataTable @"
SELECT StaffId, StaffGuid, StaffNo, StaffName, StaffChName, GroupId, CompanyId,
       DepartmentId, OrgId, ManagerId, RoleId, StaffType, StaffTitleId,
       IsActived, IsAdmin, IsManager, Status, AccessLevel, OpenId
FROM dbo.HR_Staff
ORDER BY StaffId;
"@
    $users = Get-DataTable @"
SELECT UserId, UserName, EmployeeName, CompanyId, DepartmentId, OrgId,
       IsAdmin, IsDepartmentManager, Status, AccessLevel
FROM dbo.IPR_User
ORDER BY UserId;
"@
    $userRoles = Get-DataTable @"
SELECT UserRoleId, UserId, RoleId, CreateUser, CreateTime, ChangeUser, ChangeTime
FROM dbo.IPR_UserRole
ORDER BY UserId, RoleId, UserRoleId;
"@

    $menus | Export-Csv (Join-Path $OutputDirectory "authorization-menus.csv") -NoTypeInformation -Encoding UTF8
    $roles | Export-Csv (Join-Path $OutputDirectory "authorization-roles.csv") -NoTypeInformation -Encoding UTF8
    $permissions | Export-Csv (Join-Path $OutputDirectory "authorization-role-permissions.csv") -NoTypeInformation -Encoding UTF8
    $staff | Export-Csv (Join-Path $OutputDirectory "authorization-staff.csv") -NoTypeInformation -Encoding UTF8
    $users | Export-Csv (Join-Path $OutputDirectory "authorization-users.csv") -NoTypeInformation -Encoding UTF8
    $userRoles | Export-Csv (Join-Path $OutputDirectory "authorization-user-roles.csv") -NoTypeInformation -Encoding UTF8

    [ordered]@{
        exported_at = (Get-Date).ToString("o")
        menus = $menus.Rows.Count
        roles = $roles.Rows.Count
        role_permissions = $permissions.Rows.Count
        staff = $staff.Rows.Count
        users = $users.Rows.Count
        user_roles = $userRoles.Rows.Count
    } | ConvertTo-Json | Set-Content (Join-Path $OutputDirectory "authorization-summary.json") -Encoding UTF8
}
finally {
    $connection.Close()
}
