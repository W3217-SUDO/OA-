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
  assert.ok(saveEmployeeEdit.includes("permissionRole=normalizedAccountType===employeeAccountType?String(value.staff_role||'').trim():''"), 'staff role should remain the HR permission-role source')
  assert.ok(saveEmployeeEdit.includes("selectedSystemRole=permissionRole?systemRoleOf(permissionRole):'user'"), 'business permission role should map back to base system role')
  assert.ok(saveEmployeeEdit.includes("effectivePosition=normalizedAccountType==='客户账号'?'客户联系人':value.position"), 'customer accounts should use the customer-contact position')
  assert.ok(saveEmployeeEdit.includes("editableData.staff_role=normalizedAccountType==='客户账号'?'客户联系人':permissionRole"), 'staff role should follow account type')
  assert.ok(saveEmployeeEdit.includes('editableData.permission_role=permissionRole'), 'business permission role marker should be preserved in employee data')
})

test('contract approval qualification is directly configurable for every persisted employee', () => {
  assert.ok(source.includes('const canConfigureContractApproval='), 'HR page should centralize contract approval eligibility')
  assert.ok(
    source.includes('canConfigureContractApproval=(employeeId?:number)=>Boolean(employeeId&&employeeId>0)'),
    'save path should only require a persisted employee record',
  )
  assert.ok(
    saveEmployeeEdit.includes('editableData.contract_approval_enabled=Boolean(value.contract_approval_enabled)'),
    'save path should preserve the selected approval setting without role coercion',
  )
  assert.ok(
    editModal.includes('disabled={!canConfigureContractApproval(editingEmployee?.id)||savingEmployee}'),
    'contract approval switch should remain enabled for admin and non-employee account types',
  )
})

test('role changes do not clear the independently configured contract approval flag', () => {
  assert.ok(!source.includes("if(!editingEmployee)return;if(!canConfigureContractApproval"), 'role/account changes must not clear the switch')
})

test('hr edit keeps only the contract approval eligibility switch, not the removed relationship shortcut', () => {
  assert.ok(!source.includes("openHrAdminNavigation('contract-approver-settings'"), 'HR edit modal should not link to the removed approval relationship shortcut')
  assert.ok(editModal.includes('contract_approval_enabled'), 'HR edit modal should keep the direct eligibility switch')
  assert.ok(!editModal.includes('审批关系'), 'approval relationship text should not appear in HR edit modal')
})

test('employee personnel-name display uses the recorded name metadata instead of username fallback', () => {
  assert.ok(source.includes("const PERSON_NAME_PLACEHOLDER='姓名待维护'"), 'HR page should use the shared placeholder for missing personnel names')
  assert.ok(source.includes('const personDisplayName='), 'HR page should centralize personnel-name rendering')
  assert.ok(source.includes('personDisplayName(r)'), 'employee table should render the display-name helper')
  assert.ok(source.includes('display_name_missing'), 'employee page should surface missing Chinese-name metadata')
  assert.ok(source.includes("String(row.person_display_name||'').trim()"), 'recorded English or job-title-like names should remain visible')
  assert.ok(source.includes('请在修改入口补充姓名'), 'HR edit entry should guide administrators to complete names')
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
