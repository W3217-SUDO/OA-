export function hrActionAccess(role) {
  const isAdmin = role === 'admin'
  return {
    canEditEmployee: isAdmin,
    canProcessStatus: isAdmin || role === 'manager',
    canManageAccount: isAdmin,
    canDeleteEmployee: isAdmin,
  }
}

export function organizationActionAccess(role) {
  return { canManageOrganization: role === 'admin' }
}

// Keep the built-in administrator role available; the API enforces the same
// invariant so UI and direct requests cannot diverge.
export function canDeleteOrganizationRole(roleCode) {
  return roleCode !== 'SYSTEM-ADMIN'
}
