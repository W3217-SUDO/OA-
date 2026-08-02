import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const oldRoot = new URL('../../../旧系统归档源码/SH.CRM.WEB/', import.meta.url)
const oldContract = await readFile(new URL('Areas/FCM/Controllers/ContractController.cs', oldRoot), 'utf8')
const oldCase = await readFile(new URL('Areas/IPR/Controllers/CaseCustomerController.cs', oldRoot), 'utf8')
const oldEvents = await readFile(new URL('Areas/CRM/Controllers/ContractEventController.cs', oldRoot), 'utf8')
const oldShare = await readFile(new URL('Areas/CRM/Controllers/CustomerShareController.cs', oldRoot), 'utf8')
const localPage = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
const localRelation = await readFile(new URL('./src/customerRelationNavigation.ts', import.meta.url), 'utf8')

test('customer contract and case relation actions preserve stable identifiers before navigation', () => {
  assert.match(oldContract, /GetContractListByCustomerNo\(string customerNo\)/)
  assert.match(oldCase, /CaseCustomerListSelected\(CaseCustomerSelectedModel model\)/)
  assert.match(localPage, /rememberCustomerRelationTarget\(\{ id: customer\.id, serial_no: customer\.serial_no, title: customer\.title, target: "contracts" \}\)/)
  assert.match(localPage, /rememberCustomerRelationTarget\(\{ id: customer\.id, serial_no: customer\.serial_no, title: customer\.title, target: "civil-cases" \}\)/)
  assert.match(localRelation, /sessionStorage\.setItem\(STORAGE_KEY/)
})

test('customer relation targets are one-shot and expire instead of leaking to a later page', () => {
  assert.match(localRelation, /sessionStorage\.removeItem\(STORAGE_KEY\)/)
  assert.match(localRelation, /MAX_AGE_MS/)
  assert.match(localRelation, /Date\.now\(\) - Number\(parsed\.at\)/)
})

test('shared customer UI keeps recipient projection while legacy API remains separately documented', () => {
  assert.match(oldShare, /CustomerSharedObjects\(long customerId\)/)
  assert.match(oldShare, /List<BizCustomerCoordinator>/)
  assert.match(localPage, /r\.data\.shared_with/)
  assert.match(localPage, /target: "contracts"|target: "civil-cases"/)
})

test('customer event detail keeps legacy content/operator/time columns and actionable empty state', () => {
  assert.match(oldEvents, /CustomerEvents\(string customerGuid\)/)
  assert.match(oldEvents, /CustomerEventCreate\(string customerGuid,string content\)/)
  assert.match(oldEvents, /customerEvent\.Content/)
  assert.match(localPage, /dataSource=\{contacts\.data\.notes \|\| \[\]\}/)
  assert.match(localPage, /dataIndex:"content"/)
  assert.match(localPage, /dataIndex:"operator"/)
  assert.match(localPage, /dataIndex:"created_at"/)
})

test('customer event and customerGuid backend gaps are not disguised as frontend capabilities', () => {
  assert.doesNotMatch(localPage, /CustomerEventCreate|CustomerSharedObjects|customerGuid/)
})
