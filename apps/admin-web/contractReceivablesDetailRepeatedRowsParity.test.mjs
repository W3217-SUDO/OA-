import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractReceivablesPage.tsx', import.meta.url), 'utf8')

test('receivables detail shows the contract and row amounts on every fee row', () => {
  assert.doesNotMatch(source, /isRepeatedReceivableDetailRow/, 'detail rows must not hide repeated contracts')
  assert.match(source, /detailColumns[\s\S]*?onClick=\{\(\) => openContract\(row\)\}/, 'each row must retain its contract link')
  assert.match(source, /receivableDetailAmounts\(row\)\[key as keyof ReturnType/, 'amount cells must use the current fee row')
})
