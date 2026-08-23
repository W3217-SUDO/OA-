import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
const customerStyles = await readFile(new URL('./src/customer-center.css', import.meta.url), 'utf8')

test('my-customer query exposes the legacy search action without unrelated global controls', () => {
  const queryActions = source.match(/<div className="customer-query">[\s\S]*?<\/div>\s*<Table/)?.[0] ?? ''
  assert.match(queryActions, /onClick=\{queryCustomerList\}/)
  assert.match(queryActions, /\{!isOriginalCustomerList &&\s*<Button icon=\{<ReloadOutlined \/>\}/)
})

test('customer query layout remains readable within customer-owned CSS', () => {
  assert.match(customerStyles, /\.customer-query\s*\{[\s\S]*?grid-template-columns:\s*auto 150px auto 140px auto 150px auto;/)
  assert.match(customerStyles, /\.customer-original-pagination[\s\S]*?min-width:/)
})
