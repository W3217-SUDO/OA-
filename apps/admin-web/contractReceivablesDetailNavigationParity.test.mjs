import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractReceivablesPage.tsx', import.meta.url), 'utf8')

test('receivables contract numbers open the receivables-detail route with an exact contract filter', () => {
  const returnView = source.match(/export const receivableDetailReturnView = \(initialView: string\) => ([^;]+);/)
  const matchesContract = source.match(/export const matchesReceivableDetailContract = \(detailContractNo: unknown, contractNo: unknown\) => ([^;]+);/)

  assert.ok(returnView, 'detail navigation must retain the source receivables view')
  assert.ok(matchesContract, 'detail rows must support exact contract filtering')
  const resolveReturnView = new Function('initialView', `return (${returnView[1]});`)
  const matches = new Function('detailContractNo', 'contractNo', `return (${matchesContract[1]});`)

  assert.equal(resolveReturnView('contract-receivable-mine'), 'contract-receivable-mine')
  assert.equal(resolveReturnView('contract-receivable-dept'), 'contract-receivable-dept')
  assert.equal(resolveReturnView('contract-receivable-company'), 'contract-receivable-company')
  assert.equal(matches('SHHT2610056', 'SHHT2610056'), true)
  assert.equal(matches('SHHT2610056', 'SHHT2610055'), false)
  assert.equal(matches('', 'SHHT2610056'), true)
  assert.match(source, /sessionStorage\.setItem\("sunhold:receivable-detail-context", JSON\.stringify\(\{ contract_no: contractNo, return_view: receivableDetailReturnView\(initialView\) \}\)\)/)
  assert.match(source, /setDetailContext\(\{ contract_no: contractNo, return_view: receivableDetailReturnView\(initialView\) \}\)/)
  assert.match(source, /onNavigate\?\.\("contract-receivable-detail"\)/)
})
