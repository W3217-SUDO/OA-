import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const source = await readFile(
  fileURLToPath(new URL('./src/HrCenterPage.tsx', import.meta.url)),
  'utf8',
)

function block(startNeedle, endNeedle) {
  const start = source.indexOf(startNeedle)
  assert.notEqual(start, -1, 'missing source anchor: ' + startNeedle)
  const end = endNeedle ? source.indexOf(endNeedle, start) : source.length
  assert.notEqual(end, -1, 'missing source end anchor: ' + endNeedle)
  return source.slice(start, end)
}

const departmentChange = block('const handleDepartmentFilterChange=', 'const saveEmployee=')
const listPanel = block('const listPanel=', 'const basicFields:')
const editModal = block('const editModal=', 'const transitionModal=')

test('department filter change clears stale employee selection and delete preflight state', () => {
  assert.ok(departmentChange.includes('setDepartment(value||\'\')'), 'department helper should own the filter value')
  assert.ok(departmentChange.includes('setSelectedEmployeeIds([])'), 'changing department should clear selected employees from the prior list')
  assert.ok(departmentChange.includes('setBatchDeletionImpact(null)'), 'changing department should close stale batch deletion impact')
  assert.ok(departmentChange.includes('setDeletingEmployee(null)') && departmentChange.includes('setDeletionImpact(null)'), 'changing department should clear stale single-delete impact')
})

test('department filter change clears stale edit and approval relationship context', () => {
  assert.ok(departmentChange.includes('setEditingEmployee(null)'), 'changing department should close stale employee edit modal')
  assert.ok(departmentChange.includes('employeeEditForm.resetFields()'), 'changing department should reset edit form state and approval relationship context')
  assert.ok(editModal.includes('审批关系'), 'approval relationship entry should live in the edit modal')
  assert.ok(editModal.includes('actionAccess.canManageAccount'), 'approval relationship entry remains admin-gated after filter changes')
})

test('department select uses the reset helper instead of direct state assignment', () => {
  assert.ok(listPanel.includes('onChange={handleDepartmentFilterChange}'), 'department select should use the cleanup helper')
  assert.ok(!listPanel.includes('onChange={setDepartment}'), 'department select must not bypass cleanup with direct setDepartment')
})
