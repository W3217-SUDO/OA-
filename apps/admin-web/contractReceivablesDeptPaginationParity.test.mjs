import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractReceivablesPage.tsx', import.meta.url), 'utf8')

test('department receivables keeps the legacy page size selector and one-page GO control', () => {
  const paginationHelper = source.match(/export const shouldUseMyReceivablesPagination = \(initialView: string\) => ([^;]+);/)
  const jumperHelper = source.match(/export const shouldShowMyReceivablesSinglePageJumper = \(initialView: string, rowCount: number, pageSize: number\) => ([^;]+);/)

  assert.ok(paginationHelper, 'receivables pagination helper must exist')
  assert.ok(jumperHelper, 'receivables single-page jumper helper must exist')
  const shouldPaginate = new Function('initialView', `return (${paginationHelper[1]});`)
  const shouldShowJumper = new Function('initialView', 'rowCount', 'pageSize', `return (${jumperHelper[1]});`)

  assert.equal(shouldPaginate('contract-receivable-dept'), true)
  assert.equal(shouldShowJumper('contract-receivable-dept', 1, 10), true)
  assert.equal(shouldShowJumper('contract-receivable-dept', 11, 10), false)
})
