import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractCenterPage.tsx', import.meta.url), 'utf8')

test('contract detail exposes object and attachment actions with API guards', () => {
  assert.match(source, /新增标的/)
  assert.match(source, /deleteContractObject\(row\.id\)/)
  assert.match(source, /上传附件/)
  assert.match(source, /api\.post\("\/attachments"/)
  assert.match(source, /api\.get\(`\/attachments\/\$\{item\.id\}\/preview`\)/)
  assert.match(source, /api\.delete\(`\/attachments\/\$\{item\.id\}`\)/)
  assert.match(source, /contractFile\.size > 20 \* 1024 \* 1024/)
  assert.match(source, /setAttachmentPreview\(/)
  assert.match(source, /在线查看：/)
  assert.match(source, /accept="\.pdf,\.doc,\.docx,\.xls,\.xlsx,\.ppt,\.pptx,\.txt,\.png,\.jpg,\.jpeg,\.zip,\.rar"/)
  assert.match(source, /disabled=\{!viewing \|\| \["审批中", "已归档"\]\.includes\(viewing\.status\)\}/)
  assert.ok((source.match(/disabled=\{!viewing \|\| \["审批中", "已归档"\]\.includes\(viewing\.status\)\}/g) || []).length >= 5)
  assert.match(source, /disabled=\{!contractFile \|\| !viewing \|\| \["审批中", "已归档"\]\.includes\(viewing\.status\)\}/)
  assert.match(source, /Popconfirm title="确认删除该合同附件？" disabled=/)
  assert.match(source, /合同附件预览失败/)
})
