import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

test('my customer actions expose guarded delete and recycle confirmation', () => {
  assert.match(source, /initialView === "customer-mine"[\s\S]*?key: "delete", label: "客户删除"/)
  assert.match(source, /const requireSingleSelected = \(\) =>/)
  assert.match(source, /if \(key === "delete"\) recycleCustomer\(target\)/)
  assert.match(source, /api\.post\(`\/customers\/\$\{row\.id\}\/recycle`/)
  assert.match(source, /setSelectedRowKeys\(\[\]\)/)
})
