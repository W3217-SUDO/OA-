import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const page = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

test('company customers open the complete shared customer editor', () => {
  assert.match(
    page,
    /initialView === "customer-company"[\s\S]*\{ key: "edit", label: "客户编辑" \}/,
  )
  assert.match(page, /if \(key === "edit"\) startEdit\(target\)/)
  assert.match(page, /const renderCustomerRelatedTabs = \(showSaveButton: boolean\) => \(/)
  for (const label of ['联系人', '事项记录', '客户文档']) {
    assert.match(page, new RegExp(`label: "${label}"`))
  }
  assert.match(page, /\{editing && renderCustomerRelatedTabs\(false\)\}/)
})
