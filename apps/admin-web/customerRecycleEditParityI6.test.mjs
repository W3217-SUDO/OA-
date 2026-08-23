import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

test('customer edit keeps the customer name editable like the legacy form', () => {
  const titleFieldStart = source.indexOf('label="客户名称" name="title"')
  const statusFieldStart = source.indexOf('name="status"', titleFieldStart)
  assert.ok(titleFieldStart >= 0)
  assert.ok(statusFieldStart > titleFieldStart)
  const titleField = source.slice(titleFieldStart, statusFieldStart)
  assert.match(titleField, /name="title"[\s\S]*?<Input\s*\/>/)
  assert.doesNotMatch(titleField.slice(0, titleField.indexOf('</Form.Item>')), /disabled=/)
})
