import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

test('company customer detail matches the legacy empty documents guidance', () => {
  assert.match(
    source,
    /locale=\{\{emptyText: \["customer-shared", "customer-company"\]\.includes\(initialView\) \? "没有查询到客户文件，可以去 上传客户文件" : "没有查询到客户文件"\}\}/,
  )
})
