import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
const styles = await readFile(new URL('./src/styles.css', import.meta.url), 'utf8')
const dashboardStyles = await readFile(new URL('./src/dashboard.css', import.meta.url), 'utf8')
const customerStyles = await readFile(new URL('./src/customer-center.css', import.meta.url), 'utf8')

test('my-customer query exposes only the legacy search action', () => {
  const queryActions = source.match(/<div className="customer-query">[\s\S]*?<\/div>\s*<Table/)?.[0] ?? ''

  assert.match(queryActions, /onClick=\{queryCustomerList\}/)
  assert.match(queryActions, /\{!isOriginalCustomerList &&\s*<Button icon=\{<ReloadOutlined \/>\}/)
})

test('customer list visual affordances keep the header and query controls readable', () => {
  assert.match(styles, /\.workspace-tabs[\s\S]*?\.ant-tabs-nav-more[\s\S]*?content:\s*["']▾["']/)
  assert.match(styles, /\.global-search\s*\{[\s\S]*?margin-left:\s*(?:2[8-9]|[3-9]\d)px;/)
  assert.match(dashboardStyles, /\.global-search\{width:440px;margin-left:(?:2[8-9]|[3-9]\d)px\}/)
  assert.match(customerStyles, /\.customer-query\s*\{[\s\S]*?grid-template-columns:\s*auto 150px auto 140px auto 150px auto;/)
})
