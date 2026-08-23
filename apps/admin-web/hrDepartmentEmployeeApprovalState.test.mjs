import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const source = await readFile(fileURLToPath(new URL('./src/HrCenterPage.tsx', import.meta.url)), 'utf8')

function block(startNeedle, endNeedle) {
  const start = source.indexOf(startNeedle)
  assert.notEqual(start, -1, 'missing source anchor: ' + startNeedle)
  const end = source.indexOf(endNeedle, start)
  assert.notEqual(end, -1, 'missing source end anchor: ' + endNeedle)
  return source.slice(start, end)
}

const departmentChange = block('const handleDepartmentFilterChange=', 'const saveEmployee=')
const listPanel = block('const listPanel=', 'const basicFields:')
const editModal = block('const editModal=', 'const transitionModal=')

test('department change clears stale selection and deletion preflight state', () => {
  for (const reset of ['setDepartment(value||\'\')', 'setSelectedEmployeeIds([])', 'setBatchDeletionImpact(null)', 'setDeletingEmployee(null)', 'setDeletionImpact(null)']) {
    assert.ok(departmentChange.includes(reset))
  }
})

test('department change closes and resets the employee editor without obsolete approval controls', () => {
  assert.ok(departmentChange.includes('setEditingEmployee(null)'))
  assert.ok(departmentChange.includes('employeeEditForm.resetFields()'))
  assert.ok(!editModal.includes('approval relationship'))
  assert.ok(!editModal.includes('ApprovalRelation'))
})

test('department select uses the cleanup helper', () => {
  assert.ok(listPanel.includes('onChange={handleDepartmentFilterChange}'))
  assert.ok(!listPanel.includes('onChange={setDepartment}'))
})
