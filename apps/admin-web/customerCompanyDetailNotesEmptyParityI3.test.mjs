import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

test('company customer detail matches the legacy empty notes guidance', () => {
  assert.match(
    source,
    /locale=\{\{emptyText: \["customer-shared", "customer-company"\]\.includes\(initialView\) \? "没有查询到事项记录，可以去 新建" : "没有查询到事项记录"\}\}/,
  )
})
