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

test('hr edit keeps only the contract approval eligibility switch, not the removed relationship shortcut', () => {
  assert.ok(!source.includes("openHrAdminNavigation('contract-approver-settings'"), 'HR edit modal should not link to the removed approval relationship shortcut')
  assert.ok(editModal.includes('contract_approval_enabled'), 'HR edit modal should keep the direct eligibility switch')
  assert.ok(!editModal.includes('审批关系'), 'approval relationship text should not appear in HR edit modal')
})

test('employee personnel-name display uses the recorded name metadata instead of username fallback', () => {
  assert.ok(source.includes("const PERSON_NAME_PLACEHOLDER='【待补充中文姓名】"), 'HR page should use a clear Chinese placeholder for missing personnel names')
  assert.ok(source.includes('const personDisplayName='), 'HR page should centralize personnel-name rendering')
  assert.ok(source.includes('personDisplayName(r)'), 'employee table should render the display-name helper')
  assert.ok(source.includes('display_name_missing'), 'employee page should surface missing Chinese-name metadata')
  assert.ok(source.includes("String(row.person_display_name||'').trim()"), 'recorded English or job-title-like names should remain visible')
  assert.ok(source.includes('请在修改入口补充中文姓名'), 'HR edit entry should guide administrators to complete Chinese names')
  assert.doesNotMatch(source, /display_name:\s*account\?\.display_name\|\|row\.title/)
})

test('employee view is read-only while edit modal owns leave matter archive and commission maintenance', () => {
  const employeeTabs = block('const employeeTabs=', 'const newPanel=')
  const detailModal = block('const detail=', 'const editModal=')
  const editModal = block('const editModal=', 'const transitionModal=')

  assert.match(employeeTabs, /canManageSubrecords=actionAccess\.canProcessStatus/)
  assert.match(employeeTabs, /canManage=\{canManageSubrecords\}/)
  assert.match(detailModal, /employeeTabs\(viewing\.id,details,false\)/)
  assert.match(editModal, /employeeTabs\(editingEmployee\.id,<Form/)
  assert.match(editModal, /,true\)\}<\/Modal>/)
})
