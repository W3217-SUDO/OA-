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

const saveEmployee = block('const saveEmployee=', 'const openEmployeeEdit=')
const saveEmployeeEdit = block('const saveEmployeeEdit=', 'const openTransition=')
const basicPanel = block('const basic=', 'const employeeTabs=')
const editModal = block('const editModal=', 'const transitionModal=')

test('new employee approval switch is tied to employee system-account eligibility', () => {
  assert.ok(source.includes('const employeeAccountType='), 'new employee approval eligibility should use the shared employee account type')
  assert.ok(source.includes("Form.useWatch('account_type',form)"), 'new employee form should react to account type changes')
  assert.ok(source.includes("form.setFieldValue('contract_approval_enabled',false)"), 'switching away from employee account should clear stale approval eligibility')
  assert.ok(
    saveEmployee.includes('contract_approval_enabled:normalizedAccountType===employeeAccountType&&Boolean(value.contract_approval_enabled)'),
    'new employee save should not persist approval eligibility for customer/external profiles',
  )
  assert.ok(
    basicPanel.includes('disabled={!newEmployeeCanConfigureContractApproval}'),
    'new employee approval switch should be disabled for profiles without a system user',
  )
})

test('employee edit approval switch follows account type, role and formal HR record eligibility', () => {
  assert.ok(source.includes("Form.useWatch('account_type',employeeEditForm)"), 'edit form should react to account type changes')
  assert.ok(
    source.includes('canConfigureContractApproval=(systemRole:string,employeeId?:number,accountType=employeeAccountType)'),
    'shared approval guard should include account type',
  )
  assert.ok(
    saveEmployeeEdit.includes('canConfigureContractApproval(roleValue,editingEmployee.id,normalizedAccountType)'),
    'edit save should use selected account type when deciding approval eligibility',
  )
  assert.ok(
    editModal.includes('disabled={!canConfigureContractApproval(editingSystemRole,editingEmployee?.id,editingAccountType)||savingEmployee}'),
    'edit approval switch should be disabled when account type or role is ineligible',
  )
})

test('employee edit approval switch normalizes legacy account type and persists approval eligibility', () => {
  assert.ok(source.includes('const normalizeAccountType='), 'legacy employees with missing account_type should be normalized before approval checks')
  assert.ok(
    source.includes("const editingAccountType=normalizeAccountType(Form.useWatch('account_type',employeeEditForm))"),
    'edit approval guard should not treat blank legacy account_type as ineligible',
  )
  assert.ok(
    saveEmployeeEdit.includes('account_type:normalizedAccountType'),
    'edit save should persist normalized account type so refresh keeps the approval flag eligible',
  )
  assert.ok(
    saveEmployeeEdit.includes('editableData.contract_approval_enabled=canAssignContractApproval&&Boolean(value.contract_approval_enabled)'),
    'edit save should keep the selected approval flag when the employee is eligible',
  )
})

test('employee edit approval switch saves directly to contract approver backend', () => {
  assert.ok(
    source.includes('const applyEmployeeContractApprovalStatus=async(checked:boolean)'),
    'edit approval switch should have a dedicated save handler',
  )
  assert.ok(
    source.includes("api.patch(`/hr/employees/${editingEmployee.id}/contract-approval-status`,{contract_approval_enabled:checked})"),
    'approval switch should immediately persist to the HR contract-approval endpoint',
  )
  assert.ok(
    editModal.includes('onChange={(checked)=>void applyEmployeeContractApprovalStatus(checked)}'),
    'approval switch should call the direct save handler when toggled',
  )
})

test('employee edit approval switch keeps modal and outer list state bound to backend truth', () => {
  assert.ok(
    source.includes('const editingContractApprovalEnabled=Boolean(Form.useWatch(\'contract_approval_enabled\',employeeEditForm))'),
    'switch visual state should be controlled by the live edit form value',
  )
  assert.ok(
    editModal.includes('checked={editingContractApprovalEnabled}'),
    'switch should render the same value that the edit form stores',
  )
  assert.ok(
    source.includes('const withContractApprovalState='),
    'HR page should normalize approval state onto employee rows',
  )
  assert.ok(
    source.includes('const updatedEmployee=withContractApprovalState'),
    'opening edit should reconcile stale outer list rows with the system-account approval flag',
  )
  assert.ok(
    source.includes('const approved=Boolean(data.can_approve_contract??checked)'),
    'toggle success should trust the backend approver eligibility response',
  )
  assert.ok(
    source.includes("employeeEditForm.setFieldValue('contract_approval_enabled',approved)"),
    'toggle success should write the backend value back into the modal form',
  )
  assert.ok(
    source.includes('await load(employeePage)'),
    'toggle success should refresh the outer employee-list status from the server',
  )
})
