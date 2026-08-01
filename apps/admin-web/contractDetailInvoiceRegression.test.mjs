import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractCenterPage.tsx', import.meta.url), 'utf8')

test('contract details load finance invoices and keep only the exact contract number', () => {
  assert.match(source, /api\.get\("\/finance\/invoices",\s*\{\s*params:\s*\{\s*scope:\s*"company",\s*customer:\s*contract\.customer,\s*page:\s*1,\s*page_size:\s*100\s*\}\s*\}\)/)
  assert.match(source, /item\.data\?\.contract_no\s*===\s*contract\.serial_no/)
  assert.match(source, /item\.title\?\.includes\(contract\.serial_no\)/)
  assert.doesNotMatch(source, /module:\s*"invoice",\s*keyword:\s*contract\.serial_no/)
})
