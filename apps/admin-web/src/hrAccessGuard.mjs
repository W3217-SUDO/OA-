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
