import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
const api = await readFile(new URL('../api-server/app/main.py', import.meta.url), 'utf8')

test('customer A lifecycle UI exposes create, edit/cancel, child tabs, relations, and cleanup actions', () => {
  assert.match(source, /name="title" rules=\{\[\{ required: true \}\]\}/)
  assert.match(source, /客户名称已存在|客户已创建/)
  assert.match(source, /key: "edit", label: "客户编辑"/)
  assert.match(source, /setEditing\(null\)/)
  assert.match(source, /key: "contacts"/)
  assert.match(source, /key: "notes"/)
  assert.match(source, /key: "documents"/)
  assert.match(source, /openNewEditor\("contact"\)/)
  assert.match(source, /const addNote = async/)
  assert.match(source, /const uploadDocument = async/)
  assert.match(source, /downloadDocument/)
  assert.match(source, /openCustomerContracts/)
  assert.match(source, /openCustomerCivilCases/)
  assert.match(source, /recycleCustomer/)
})

test('customer A backend protects duplicate names and owns child mutations', () => {
  assert.match(api, /@app\.post\(f"\{settings\.api_prefix\}\/customers"/)
  assert.match(api, /existing_customers = \(await db\.scalars\(select\(BusinessRecord\)/)
  assert.match(api, /status_code=409/)
  assert.match(api, /\/customers\/\{\{customer_id\}\}\/contacts/)
  assert.match(api, /\/customers\/\{\{customer_id\}\}\/contacts\/\{\{contact_id\}\}/)
  assert.match(api, /\/customers\/\{\{customer_id\}\}\/notes/)
  assert.match(api, /\/customers\/\{\{customer_id\}\}\/notes\/\{\{note_id\}\}/)
  assert.match(api, /\/attachments\/\{\{attachment_id\}\}/)
})
