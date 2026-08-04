import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
const actionsSource = source.slice(
  source.indexOf('const originalActionItems'),
  source.indexOf('const runOriginalAction'),
)

test('company customers expose assignment plus guarded edit/delete actions', () => {
  assert.match(
    actionsSource,
    /initialView === "customer-company"\s*\?\s*\[\s*\{ key: "edit", label: "客户编辑" \}, \{ key: "delete", label: "客户删除" \}, \{ key: "assign", label: "分配客户" \}, \.\.\.customerNavigationActions\s*\]\s*:/,
  )

  const companyStart = actionsSource.indexOf('initialView === "customer-company"')
  const recycleStart = actionsSource.indexOf('["customer-recycle"', companyStart)
  const companyActions = actionsSource.slice(companyStart, recycleStart)

  assert.doesNotMatch(
    companyActions,
    /level-review|key-change-review|portal-open|portal-close/,
  )
  assert.match(companyActions, /key: "assign", label: "分配客户"/)
  assert.match(companyActions, /\.\.\.customerNavigationActions/)
})
