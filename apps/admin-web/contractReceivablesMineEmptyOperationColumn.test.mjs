import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractReceivablesPage.tsx', import.meta.url), 'utf8')

test('my receivables adds only the legacy blank header column outside detail view', () => {
  assert.match(source, /shouldUseMyReceivablesPagination\(initialView\) \? \[\.\.\.listColumns, \{ title: "", key: "legacy-empty-operation", width: \d+ \}\] : listColumns/)
  assert.match(source, /detailView \? \([\s\S]*?columns=\{detailColumns\}/)
})
