import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
const actionsSource = source.slice(
  source.indexOf('const originalActionItems'),
  source.indexOf('const runOriginalAction'),
)

test('department customers expose assignment plus navigation actions', () => {
  assert.match(
    actionsSource,
    /initialView === "customer-dept"\s*\?\s*\[\s*\{ key: "assign", label: "分配客户" \}, \.\.\.customerNavigationActions\s*\]\s*:/,
  )

  const departmentStart = actionsSource.indexOf('initialView === "customer-dept"')
  const companyStart = actionsSource.indexOf('initialView === "customer-company"')
  const departmentActions = actionsSource.slice(departmentStart, companyStart)

  assert.doesNotMatch(
    departmentActions,
    /level-review|key-change-review|portal-open|portal-close/,
  )
  assert.match(departmentActions, /key: "assign", label: "分配客户"/)
  assert.match(departmentActions, /\.\.\.customerNavigationActions/)
})
