import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

test('company customer detail uses the legacy new-note action label', () => {
  assert.match(
    source,
    /<Button type="link" onClick=\{\(\) => openNewEditor\("note"\)\}>\{initialView === "customer-company" \? "新建" : "新建事项记录"\}<\/Button>/,
  )
})
