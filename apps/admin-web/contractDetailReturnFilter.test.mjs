import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractCenterPage.tsx', import.meta.url), 'utf8')

test('contract detail navigation preserves the current list query for return', () => {
  assert.match(source, /const CONTRACT_QUERY_STORAGE_KEY = "sunhold:contract-query"/)
  assert.match(source, /sessionStorage\.setItem\(CONTRACT_QUERY_STORAGE_KEY/)
  assert.match(source, /sessionStorage\.getItem\(CONTRACT_QUERY_STORAGE_KEY\)/)
})
