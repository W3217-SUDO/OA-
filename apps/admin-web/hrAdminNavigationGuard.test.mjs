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

const navigationBlock = block('const openHrAdminNavigation=', 'const filtered=')
const columns = block('const columns:TableColumnsType<Employee>=', 'const rowSelection=')
const editModal = block('const editModal=', 'const transitionModal=')

test('HR admin navigation uses a single permission gate before changing pages', () => {
  assert.ok(navigationBlock.includes('if(!actionAccess.canManageAccount)'), 'navigation helper should block non-admin users')
  assert.ok(navigationBlock.includes('message.error'), 'blocked navigation should show an explicit permission error')
  assert.ok(navigationBlock.includes('return'), 'blocked navigation should return before any page change')
  assert.ok(navigationBlock.includes('URLSearchParams'), 'navigation helper should build a route query instead of string-splicing URLs')
  assert.ok(navigationBlock.includes('window.location.href'), 'authorized navigation should still move to the target admin page')
})

test('system user management entry is routed through the guarded navigation helper', () => {
  assert.ok(columns.includes('openHrAdminNavigation(\'system-users\''), 'row-level system user entry must use the guarded helper')
  assert.ok(!columns.includes('page=system-users'), 'row-level system user entry must not bypass the helper with a raw URL')
  assert.ok(columns.includes('actionAccess.canManageAccount'), 'system user entry remains hidden from users without account-management rights')
})

test('contract approval relationship navigation is admin-gated and does not jump when unauthorized', () => {
  assert.ok(editModal.includes('审批关系'), 'employee edit modal should expose a clear approval relationship navigation affordance')
  assert.ok(editModal.includes('openHrAdminNavigation(\'contract-approver-settings\''), 'approval relationship entry must use the guarded helper')
  assert.ok(editModal.includes('actionAccess.canManageAccount'), 'approval relationship entry should only render for account-management admins')
})
