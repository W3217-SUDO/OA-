import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractCenterPage.tsx', import.meta.url), 'utf8')

test('contract detail merges workflow history into the change/event timeline', () => {
  assert.match(source, /api\.get\(`\/records\/\$\{contract\.id\}\/history`\)/)
  assert.match(source, /workflowHistoryResult/)
})
