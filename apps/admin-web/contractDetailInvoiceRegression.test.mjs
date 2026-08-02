import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { filterContractLinkedRows } from './src/contractWorkflowPolicy.mjs'

const source = fs.readFileSync(new URL('./src/ContractCenterPage.tsx', import.meta.url), 'utf8')

test('contract details load finance invoices and keep only the exact contract number', () => {
  assert.match(source, /api\.get\("\/finance\/invoices",\s*\{\s*params:\s*\{\s*scope:\s*"company",\s*customer:\s*contract\.customer,\s*page:\s*1,\s*page_size:\s*100\s*\}\s*\}\)/)
  assert.match(source, /filterContractLinkedRows\(invoiceResult\.value\.data\.items\s*\|\|\s*\[\],\s*contract\)/)
  assert.match(source, /filterContractLinkedRows\(paymentResult\.value\.data\.items\s*\|\|\s*\[\],\s*contract\)/)
  assert.doesNotMatch(source, /item\.title\?\.includes\(contract\.serial_no\)/)
  assert.doesNotMatch(source, /module:\s*"invoice",\s*keyword:\s*contract\.serial_no/)
})

test('contract-linked rows match exact ids or contract numbers without prefix or empty-number leaks', () => {
  const rows = [
    { id: 1, title: 'HT-0010 invoice', data: { contract_no: 'HT-0010' } },
    { id: 2, contract_record_id: 7, title: 'linked by top-level id', data: {} },
    { id: 3, title: 'linked by nested id', data: { contract_id: 7 } },
    { id: 4, title: 'linked by exact number', data: { contract_no: 'HT-001' } },
    { id: 5, title: 'HT-001 unrelated title', data: {} },
    { id: 6, title: 'empty number', data: { contract_no: '' } },
  ]

  assert.deepEqual(
    filterContractLinkedRows(rows, { id: 7, serial_no: 'HT-001' }).map((row) => row.id),
    [2, 3, 4],
  )
  assert.deepEqual(filterContractLinkedRows(rows, { id: 0, serial_no: '' }), [])
})
