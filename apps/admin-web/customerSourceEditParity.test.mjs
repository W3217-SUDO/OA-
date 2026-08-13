import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { synchronizeCustomerSource } from './src/customerParity.mjs'

test('editing customer source synchronizes list and detail source fields', () => {
  const saved = synchronizeCustomerSource({ source_person: 'legacy-user', industry: 'software' }, 'current-user')
  assert.equal(saved.customer_source, 'current-user')
  assert.equal(saved.source_person, 'current-user')
  assert.equal(saved.industry, 'software')
})

test('customer creation and list prefer the current editable source field', async () => {
  const source = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
  assert.match(source, /synchronizeCustomerSource\(\{[\s\S]*?\}, v\.customer_source\)/)
  assert.match(source, /customer_source: data\.customer_source \|\| ""/)
  assert.match(source, /source_person: data\.source_person \|\| ""/)
  assert.match(source, /r\.data\.customer_source_display_name \|\| r\.data\.customer_source \|\| r\.data\.source_person \|\| r\.owner/)
  assert.match(source, /contacts\.data\.customer_source_display_name \|\|/)
})
