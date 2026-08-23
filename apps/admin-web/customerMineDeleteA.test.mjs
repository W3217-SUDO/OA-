import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

test('my customer actions do not expose delete, while company customers keep only legacy assignment', () => {
  const mineActions = source.match(/initialView === "customer-mine"\s*\?\s*\[([\s\S]*?)\]\s*: initialView === "customer-dept"/)?.[1] || ''
  assert.doesNotMatch(mineActions, /key: "delete", label: "客户删除"/)
  const companyActions = source.match(/initialView === "customer-company"\s*\?\s*\[[^\]]*\]/)?.[0] ?? ''
  assert.match(companyActions, /key: "assign"/)
  assert.doesNotMatch(companyActions, /key: "(?:edit|release|delete)"/)
})
