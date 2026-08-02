import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

test('customer edit keeps the customer name editable like the legacy form', () => {
  const editModalStart = source.indexOf('open && initialView !== "customer-new"')
  const titleFieldStart = source.indexOf('name="title"', editModalStart)
  const statusFieldStart = source.indexOf('name="status"', titleFieldStart)
  assert.ok(titleFieldStart >= 0)
  assert.ok(statusFieldStart > titleFieldStart)
  const titleField = source.slice(titleFieldStart, statusFieldStart)
  assert.match(titleField, /name="title"[\s\S]*?<Input\s*\/>/)
  assert.doesNotMatch(titleField, /disabled=\{Boolean\(editing\)\}/)
})
