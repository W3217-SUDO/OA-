const DATA_LEVELS = new Set(["公司", "部门", "本人"]);
const BASE_ROLES = new Set(["admin", "manager", "auditor", "user"]);

export function normalizeEmployeeDataLevel(value) {
  const normalized = String(value || "").trim();
  return DATA_LEVELS.has(normalized) ? normalized : "本人";
}

export function resolveEmployeeSystemRole({ permissionRole, accountRole, recordRole, staffRole, position }) {
  const permission = String(permissionRole || "").trim();
  if (permission) return `business:${permission}`;

  const storedRole = String(accountRole || recordRole || "").trim();
  if (BASE_ROLES.has(storedRole)) return storedRole;

  const businessRole = String(staffRole || position || storedRole || "").trim();
  return businessRole ? `business:${businessRole}` : "user";
}
