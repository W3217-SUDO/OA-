import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/SystemCenterPage.tsx', import.meta.url), 'utf8')
const appSource = fs.readFileSync(new URL('./src/App.tsx', import.meta.url), 'utf8')

test('notary-office route selects the notary list category', () => {
  assert.match(source, /"system-parameters-notary-office": "notary_office"/)
  assert.match(appSource, /"system-parameters-notary-office": "system-parameters-notary"/)
})
