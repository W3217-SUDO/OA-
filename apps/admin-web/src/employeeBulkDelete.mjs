export function normalizeEmployeeIds(ids) {
  const normalized = [...new Set((ids || []).filter((id) => Number.isInteger(id) && id > 0))].sort((left, right) => left - right)
  if (!normalized.length) throw new Error('请至少选择一名员工')
  return normalized
}
