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

const saveEmployeeEdit = block('const saveEmployeeEdit=', 'const openTransition=')
const editModal = block('const editModal=', 'const transitionModal=')

test('employee edit keeps business role synchronized with account role, staff role, position and permission marker', () => {
  assert.ok(saveEmployeeEdit.includes('selectedBusinessRole(value.system_role)'), 'system_role should detect business permission role selections')
  assert.ok(saveEmployeeEdit.includes('effectiveSystemRole=permissionRole?systemRoleOf(permissionRole):value.system_role'), 'business permission role should map back to base system role')
  assert.ok(saveEmployeeEdit.includes('effectivePosition=permissionRole||value.position'), 'business permission role should become the HR position')
  assert.ok(saveEmployeeEdit.includes('editableData.staff_role=permissionRole||value.staff_role'), 'business permission role should sync staff_role')
  assert.ok(saveEmployeeEdit.includes('editableData.permission_role=permissionRole'), 'business permission role marker should be preserved in employee data')
})

test('contract approval qualification follows the selected account role and is blocked for admin or non-formal accounts', () => {
  assert.ok(source.includes('const canConfigureContractApproval='), 'HR page should centralize contract approval eligibility')
  assert.ok(source.includes("Form.useWatch('system_role',employeeEditForm)"), 'contract approval UI should react to system role changes')
  assert.ok(
    saveEmployeeEdit.includes('canConfigureContractApproval(value.system_role,editingEmployee.id)'),
    'save path should evaluate approval eligibility from the selected role and employee id',
  )
  assert.ok(
    saveEmployeeEdit.includes('editableData.contract_approval_enabled=canAssignContractApproval&&Boolean(value.contract_approval_enabled)'),
    'save path should not persist approval qualification when the selected role is not eligible',
  )
  assert.ok(
    editModal.includes('disabled={!canConfigureContractApproval(editingSystemRole,editingEmployee?.id)}'),
    'contract approval switch should be disabled when admin/non-formal accounts cannot be approvers',
  )
})

test('contract approval flag is cleared immediately when role switching removes eligibility', () => {
  assert.ok(source.includes('employeeEditForm.setFieldValue(\'contract_approval_enabled\',false)'), 'role switch should clear stale approval qualification')
  assert.ok(source.includes('editingSystemRole'), 'role-switch cleanup should depend on the live selected system role')
})
