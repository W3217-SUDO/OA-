import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
const actionsSource = source.slice(
  source.indexOf('const originalActionItems'),
  source.indexOf('const runOriginalAction'),
)

test('company customers retain only the legacy assignment action', () => {
  assert.match(
    actionsSource,
    /initialView === "customer-company"\s*\?\s*\[\s*\{ key: "assign", label: "分配客户" \}\s*\]\s*:/,
  )

  const companyStart = actionsSource.indexOf('initialView === "customer-company"')
  const recycleStart = actionsSource.indexOf('["customer-recycle"', companyStart)
  const companyActions = actionsSource.slice(companyStart, recycleStart)

  assert.doesNotMatch(
    companyActions,
    /edit|delete|release|level-review|key-change-review|portal-open|portal-close|customerNavigationActions/,
  )
  assert.match(companyActions, /key: "assign", label: "分配客户"/)
  assert.doesNotMatch(companyActions, /customerNavigationActions/)
})
