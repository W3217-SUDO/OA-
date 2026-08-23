import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const page = fs.readFileSync('src/CustomerCenterPage.tsx', 'utf8')
const editStart = page.indexOf('className="customer-edit-modal"')
const editEnd = page.indexOf('<Modal\n        open={Boolean(portalResult)}', editStart)
const edit = page.slice(editStart, editEnd)

test('customer edit retains the shared customer fields', () => {
  assert.match(edit, /className="customer-create-form"/)
  for (const field of ['title', 'serial_no', 'status', 'customer_type', 'registered_address', 'customer_managers', 'contact']) {
    assert.match(edit, new RegExp(`name="${field}"`))
  }
  assert.match(edit, /name="serial_no"[^>]*rules=\{\[\{ required: true \}\]\}/)
  assert.match(edit, /name="credit_code"[^>]*>\s*<Input disabled=\{Boolean\(editing\)\}/)
})

test('customer source edit keeps the real save synchronization path', () => {
  assert.match(page, /const data = synchronizeCustomerSource\(/)
  assert.match(page, /data: filterCustomerPatchData\(editableData\)/)
  assert.match(page, /customer_source: data\.customer_source \|\| ""/)
  assert.match(page, /source_person: data\.source_person \|\| ""/)
})

test('company and department customer views keep the assignment-only menu', () => {
  const actions = page.slice(page.indexOf('const originalActionItems'), page.indexOf('const runOriginalAction'))
  for (const view of ['customer-dept', 'customer-company']) {
    const branch = new RegExp(`initialView === "${view}"\\s*\\?\\s*\\[\\s*\\{ key: "assign"[^\\]]*\\]`)
    assert.match(actions, branch)
    assert.doesNotMatch(actions, new RegExp(`initialView === "${view}"\\s*\\?\\s*\\[[^\\]]*(portal-open|portal-close|release|key: "edit"|key: "delete")`))
  }
})
