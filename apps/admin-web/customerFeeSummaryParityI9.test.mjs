import test from 'node:test'
import assert from 'node:assert/strict'
import {
  CUSTOMER_SUMMARY_FIELDS,
  filterCustomerPatchData,
  normalizeCustomerSummary,
} from './src/customerParity.mjs'

const legacySummaryFields = [
  'total_paid_case_office_fee_amount',
  'total_cashed_case_office_fee_amount',
  'total_un_cashed_case_office_fee_amount',
  'total_deficit_case_office_fee_amount',
  'total_case_non_office_fee_amount',
  'total_cashed_case_non_office_fee_amount',
  'total_un_cashed_case_non_office_fee_amount',
  'total_case_commission_fee_amount',
  'total_cashed_case_commission_fee_amount',
  'total_paid_case_commission_fee_amount',
  'total_un_paid_case_commission_fee_amount',
  'total_invoiced_amount',
  'total_invoice_over_amount',
  'total_un_invoiced_amount',
]

test('normalizeCustomerSummary preserves all fee fields and maps legacy aliases', () => {
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
  for (const field of legacySummaryFields) {
    assert.ok(CUSTOMER_SUMMARY_FIELDS.includes(field), `${field} must remain in the summary`)
    assert.equal(typeof result[field], 'number')
  }
})

test('filterCustomerPatchData removes only server fields and preserves ordinary business fields', () => {
  const result = filterCustomerPatchData({
    title: 'Acme',
    level: '签约客户',
    contacts: [{ id: 'server' }],
    notes: [{ id: 'server' }],
    shared_with: ['server'],
    contract_count: 3,
    civil_case_count: 2,
    customer_guid: 'server-guid',
    industry: '制造业',
  })
  assert.deepEqual(result, { title: 'Acme', level: '签约客户', industry: '制造业' })
})
