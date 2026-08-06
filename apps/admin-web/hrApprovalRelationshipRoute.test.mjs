import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const appSource = await readFile(
  fileURLToPath(new URL('./src/App.tsx', import.meta.url)),
  'utf8',
)
const hrSource = await readFile(
  fileURLToPath(new URL('./src/HrCenterPage.tsx', import.meta.url)),
  'utf8',
)

function block(source, startNeedle, endNeedle) {
  const start = source.indexOf(startNeedle)
  assert.notEqual(start, -1, 'missing source anchor: ' + startNeedle)
  const end = endNeedle ? source.indexOf(endNeedle, start) : source.length
  assert.notEqual(end, -1, 'missing source end anchor: ' + endNeedle)
  return source.slice(start, end)
}

const editModalBlock = block(hrSource, 'const editModal=', 'const transitionModal=')

test('HR employee edit no longer exposes the approval relationship shortcut', () => {
  assert.ok(!hrSource.includes('openHrAdminNavigation'), 'HR page should not retain approval relationship shortcut navigation')
  assert.ok(!editModalBlock.includes("openHrAdminNavigation('contract-approver-settings'"), 'employee edit modal must not use the removed route key')
  assert.ok(!editModalBlock.includes('????'), 'employee edit modal should not render approval relationship text')
  assert.ok(editModalBlock.includes('contract_approval_enabled'), 'approval eligibility switch remains in the employee form')
})

test('workspace does not expose an HR approval relationship shortcut', () => {
  assert.ok(!appSource.includes("openHrAdminNavigation('contract-approver-settings'"), 'workspace should not expose an HR shortcut to approval relationship')
  assert.ok(!hrSource.includes('contract-approver-settings'), 'HR source should not reference the approval relationship route')
})
