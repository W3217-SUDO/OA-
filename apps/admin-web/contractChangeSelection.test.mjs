import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractCenterPage.tsx', import.meta.url), 'utf8')

test('contract change selection keeps the latest row as the sole target across A to B to A', () => {
  assert.match(source, /onChange:\s*\(keys\)\s*=>\s*\{\s*setSelectedRowKeys\(keys\.length\s*\?\s*\[keys\[keys\.length\s*-\s*1\]\]\s*:\s*\[\]\);\s*setChanging\(null\);\s*\}/s)
  assert.match(source, /const selected = rows\.find\(\(row\) => row\.id === Number\(selectedRowKeys\[0\]\)\)/)
})

test('contract change submission and cancellation use and clear the same selected target', () => {
  assert.match(source, /api\.post\(`\/contracts\/\$\{changing\.id\}\/changes`/)
  assert.match(source, /onCancel=\{\(\) => \{ setChanging\(null\); setChangeFile\(null\); changeForm\.resetFields\(\); \}\}/)
})

test('contract changes retain existing attachments unless a replacement is selected', () => {
  assert.doesNotMatch(source, /if \(!changeFile\)\s*\{\s*message\.warning\("请上传合同变更附件"\)/)
  assert.match(source, /if \(changeFile\) \{[\s\S]*attachment\.append\("file", changeFile\)/)
  assert.match(source, /label="合同附件" extra="可选；未选择时保留原有附件"/)
})
