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

export function hrTransitionOptions(status) {
  if (status === '\u79bb\u804c' || status === '\u505c\u7528') return ['\u5728\u804c']
  return {
    '试用': ['在职', '离职'],
    '在职': ['离职', '停用'],
  }[status] || []
}

export function hrTransitionReasonMessage(toStatus, reason) {
  if (['离职', '停用'].includes(toStatus) && String(reason || '').trim().length < 2) {
    return '离职或停用必须填写办理原因'
  }
  return null
}
