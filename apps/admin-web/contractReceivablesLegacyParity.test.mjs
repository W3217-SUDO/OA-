import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractReceivablesPage.tsx', import.meta.url), 'utf8')

test('receivable amount links preserve the legacy detail filter matrix', () => {
  assert.match(source, /export const receivableDetailAmountFilters(?:\s*:\s*[^=]+)?\s*=\s*\{/, 'detail amount filters need an explicit legacy matrix')
  assert.match(source, /official-unreceived/, 'official unreceived amount needs a detail filter')
  assert.match(source, /official-loss/, 'official loss amount needs a detail filter')
  assert.match(source, /agency-due/, 'agency due amount needs a detail filter')
  assert.match(source, /buildReceivableDetailContext\(/, 'amount links need a shared detail context builder')
  assert.match(source, /openReceivableDetail\([^)]*,\s*"official-unreceived"/, 'per-contract official unreceived amount must open a filtered detail')
  assert.match(source, /openReceivableDetail\([^)]*,\s*"official-loss"/, 'per-contract official loss amount must open a filtered detail')
  assert.match(source, /openReceivableDetail\([^)]*,\s*"agency-due"/, 'per-contract agency due amount must open a filtered detail')
  assert.match(source, /parsed\?\.contract_no\s*\|\|\s*parsed\?\.amount_filter/, 'summary-only detail navigation must retain its filter context')
  assert.match(source, /amount_filter:\s*detailContext(?:\?\.|\.)amount_filter/, 'case return must retain the active detail filter')
})

test('receivable list keeps legacy summary rows and hides detail summary on empty results', () => {
  assert.match(source, /shouldRenderReceivablesDetailSummary\s*=\s*\(/, 'detail summary visibility needs an explicit empty-state rule')
  assert.match(source, /contract-list-summary-top/, 'receivable list needs the legacy top summary row')
  assert.match(source, /renderReceivablesListSummaryRow/, 'receivable list needs a reusable summary row renderer')
  assert.match(source, /summary=\{\(\) => .*renderReceivablesListSummaryRow/, 'receivable list needs a legacy bottom summary row')
})
