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
  assert.ok(source.includes('const newEmployeeCanConfigureContractApproval=accountType===\'员工账号\''), 'new employee approval eligibility should require an employee login account')
  assert.ok(source.includes("Form.useWatch('account_type',form)"), 'new employee form should react to account type changes')
  assert.ok(source.includes("form.setFieldValue('contract_approval_enabled',false)"), 'switching away from employee account should clear stale approval eligibility')
  assert.ok(
    saveEmployee.includes("contract_approval_enabled:value.account_type==='员工账号'&&Boolean(value.contract_approval_enabled)"),
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
    source.includes('canConfigureContractApproval=(systemRole:string,employeeId?:number,accountType=\'员工账号\')'),
    'shared approval guard should include account type',
  )
  assert.ok(
    saveEmployeeEdit.includes('canConfigureContractApproval(value.system_role,editingEmployee.id,value.account_type)'),
    'edit save should use selected account type when deciding approval eligibility',
  )
  assert.ok(
    editModal.includes('disabled={!canConfigureContractApproval(editingSystemRole,editingEmployee?.id,editingAccountType)}'),
    'edit approval switch should be disabled when account type or role is ineligible',
  )
})
