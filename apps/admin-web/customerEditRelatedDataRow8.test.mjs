import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const page = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
const css = await readFile(new URL('./src/customer-center.css', import.meta.url), 'utf8')

test('customer edit loads the selected customer related records', () => {
  assert.match(
    page,
    /const startEdit = \(r: Customer\) => \{[\s\S]*setContacts\(r\);[\s\S]*void refreshDetail\(r, 1, 15\);/,
  )
  assert.match(page, /const refreshDetail = async \([\s\S]*nextContactPage = contactPage,[\s\S]*nextContactPageSize = contactPageSize/)
})

test('customer create and edit share contacts, notes, and documents tabs', () => {
  assert.match(page, /const renderCustomerRelatedTabs = \(showSaveButton: boolean\) => \(/)
  for (const label of ['联系人', '事项记录', '客户文档']) {
    assert.match(page, new RegExp(`label: "${label}"`))
  }
  assert.match(page, /\{renderCustomerRelatedTabs\(true\)\}/)
  assert.match(page, /\{editing && renderCustomerRelatedTabs\(false\)\}/)
})

test('customer edit uses a full-width scrollable work surface', () => {
  assert.match(page, /width="calc\(100vw - 64px\)"[\s\S]*className="customer-edit-modal"/)
  assert.match(css, /\.customer-edit-modal \.ant-modal-body \{ max-height: calc\(100dvh - 180px\); overflow-x: hidden; overflow-y: auto; \}/)
})
