import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const page = fs.readFileSync(new URL('./src/ContractReceivablesPage.tsx', import.meta.url), 'utf8')
const app = fs.readFileSync(new URL('./src/App.tsx', import.meta.url), 'utf8')

test('dashboard unpaid official fee opens the persistent receivable detail view', () => {
  assert.match(app, /const navigateMetric =/)
  assert.match(app, /sunhold:receivable-detail-context/)
  assert.match(app, /navigateMetric\(m\)/)
  assert.match(page, /api\.get\("\/receivables\/detail"\)/)
  assert.doesNotMatch(page, /removeItem\("sunhold:receivable-detail-context"\)/)
})

test('receivable details use server-projected contract, case, fee, and owner fields', () => {
  assert.match(page, /detailContext\?\.owner && item\.owner !== detailContext\.owner/)
  assert.match(page, /detail\.fee_category === "official"/)
  assert.match(page, /detail\.paid_amount/)
  assert.match(page, /const remainsDue = Number\(row\.remaining_amount \|\| 0\) > 0/)
  assert.match(page, /dataIndex: "case_stage"/)
  assert.match(page, /dataIndex: "case_type"/)
  assert.match(page, /dataIndex: "fee_type"/)
  assert.match(page, /detailTotalsByContract/)
})
