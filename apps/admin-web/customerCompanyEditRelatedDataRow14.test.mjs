import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const page = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

test('customer editing keeps the complete shared customer editor', () => {
  assert.match(page, /if \(key === "edit"\) startEdit\(target\)/)
  assert.match(page, /const renderCustomerRelatedTabs = \(showSaveButton: boolean\) => \(/)
  assert.match(page, /name="title"/)
  assert.match(page, /name="customer_managers"/)
  assert.match(page, /key: "documents"/)
  assert.match(page, /\{editing && renderCustomerRelatedTabs\(false\)\}/)
})
