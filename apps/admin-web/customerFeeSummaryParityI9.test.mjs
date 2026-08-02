import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { filterCustomerPatchData, normalizeCustomerSummary } from './src/customerParity.mjs'

const oldScript = await readFile(new URL('../../../旧系统归档源码/SH.CRM.WEB/Scripts/CRM/Customer/CRM.Customer.js', import.meta.url), 'utf8')
const localPage = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
const localParity = await readFile(new URL('./src/customerParity.mjs', import.meta.url), 'utf8')

const legacySummaryFields = [
  'totalPaidCaseOfficeFeeAmount',
  'totalCashedCaseOfficeFeeAmount',
  'totalUnCashedCaseOfficeFeeAmount',
  'totalDeficitCaseOfficeFeeAmount',
  'totalCaseNonOfficeFeeAmount',
  'totalCashedCaseNonOfficeFeeAmount',
  'totalUnCashedCaseNonOfficeFeeAmount',
  'totalCaseCommissionFeeAmount',
  'totalCashedCaseCommissionFeeAmount',
  'totalPaidCaseCommissionFeeAmount',
  'totalUnPaidCaseCommissionFeeAmount',
  'totalInvoicedAmount',
  'totalInvoiceOverAmount',
  'totalUnInvoicedAmount',
]

test('legacy customer list computes all fourteen fee summary fields', () => {
  for (const field of legacySummaryFields) assert.match(oldScript, new RegExp(`\\b${field}\\b`))
})

test('local customer list normalizes every legacy fee summary field without dropping zero values', () => {
  for (const field of legacySummaryFields) {
    const snake = field.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`)
    assert.match(localParity, new RegExp(`\\b${snake}\\b`))
  }
  assert.match(localPage, /normalizeCustomerSummary/)
  assert.match(localPage, /setListSummary\(normalizeCustomerSummary\(/)
})

test('normalizeCustomerSummary maps legacy lowerCamel, snake_case and PascalCase values', () => {
  const result = normalizeCustomerSummary({
    totalPaidCaseOfficeFeeAmount: 12.5,
    total_cashed_case_office_fee_amount: 0,
    TotalUnCashedCaseOfficeFeeAmount: 4,
    totalInvoiceOverAmount: null,
    totalUnInvoicedAmount: 'not-a-number',
  })
  assert.equal(result.total_paid_case_office_fee_amount, 12.5)
  assert.equal(result.total_cashed_case_office_fee_amount, 0)
  assert.equal(result.total_un_cashed_case_office_fee_amount, 4)
  assert.equal(result.total_invoice_over_amount, 0)
  assert.equal(result.total_un_invoiced_amount, 0)
  for (const field of legacySummaryFields) assert.equal(typeof result[field.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`)], 'number')
})

test('filterCustomerPatchData removes only server fields and preserves ordinary business fields', () => {
  const result = filterCustomerPatchData({
    title: 'Acme',
    level: '签约客户',
    contacts: [{ id: 'server' }],
    notes: [{ id: 'server' }],
    shared_with: ['server'],
    contract_count: 3,
    customer_guid: 'server-guid',
    industry: '制造业',
  })
  assert.deepEqual(result, { title: 'Acme', level: '签约客户', industry: '制造业' })
})

test('customer PATCH payload excludes server-owned relationship projections', () => {
  assert.match(localPage, /filterCustomerPatchData/)
  assert.match(localPage, /filterCustomerPatchData\((?:data|editableData)\)/)
  for (const field of ['contacts', 'notes', 'shared_with', 'contract_count', 'civil_case_count', 'customer_guid']) {
    assert.match(localParity, new RegExp(`['"]${field}['"]`))
  }
})
