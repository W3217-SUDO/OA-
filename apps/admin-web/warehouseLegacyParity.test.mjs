import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/WarehousePage.tsx', import.meta.url), 'utf8')

test('warehouse storage tree keeps the legacy count brackets', () => {
  assert.match(source, /title:`\$\{warehouseName\}【\$\{total\}】`/)
  assert.match(source, /title:`\$\{locationName\}【\$\{count\}】`/)
})

test('warehouse storage tree starts collapsed like the legacy zTree', () => {
  assert.doesNotMatch(source, /<Tree blockNode defaultExpandAll/)
  assert.match(source, /<Tree blockNode virtual=\{false\}/)
})
