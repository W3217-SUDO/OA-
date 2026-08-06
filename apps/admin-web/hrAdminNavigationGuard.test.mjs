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

const columns = block('const columns:TableColumnsType<Employee>=', 'const rowSelection=')
const editModal = block('const editModal=', 'const transitionModal=')

test('standalone system user management entry is removed from employee rows', () => {
  assert.ok(!columns.includes("openHrAdminNavigation('system-users'"), 'employee rows should not open the old standalone system user page')
  assert.ok(!columns.includes('page=system-users'), 'employee rows must not link to the removed standalone page')
  assert.ok(!columns.includes('>????<'), 'employee row actions should not expose a duplicate system user button')
  assert.ok(columns.includes('openPasswordReset'), 'password reset stays available inside employee management')
})

test('contract approval relationship shortcut is removed from employee edit modal', () => {
  assert.ok(!source.includes('openHrAdminNavigation'), 'HR page should not keep a shortcut navigation helper for approval relationship')
  assert.ok(!editModal.includes('contract-approver-settings'), 'employee edit modal must not link to approval relationship settings')
  assert.ok(!editModal.includes('????'), 'employee edit modal should not expose the removed approval relationship shortcut')
  assert.ok(editModal.includes('contract_approval_enabled'), 'contract approval eligibility switch itself stays available')
})
