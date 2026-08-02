import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractReceivablesPage.tsx', import.meta.url), 'utf8')

test('receivables detail blanks contract and seven amount cells on repeated contract rows', () => {
  assert.match(source, /export const isRepeatedReceivableDetailRow = \(/, 'detail rows need a repeated-contract predicate')
  assert.match(source, /isRepeatedReceivableDetailRow\([^)]*\)\s*\?\s*null/, 'contract and amount cells must render empty on repeats')
  assert.match(source, /detailColumns[\s\S]*?isRepeatedReceivableDetailRow[\s\S]*?contractById/, 'detail columns must apply repeat handling')
})
