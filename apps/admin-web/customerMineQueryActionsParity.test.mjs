import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

test('my-customer query exposes only the legacy search action', () => {
  const queryActions = source.match(/<div className="customer-query">[\s\S]*?<\/div>\s*<Table/)?.[0] ?? ''

  assert.match(queryActions, /onClick=\{queryCustomerList\}/)
  assert.match(queryActions, /\{!isOriginalCustomerList &&\s*<Button icon=\{<ReloadOutlined \/>\}/)
})
