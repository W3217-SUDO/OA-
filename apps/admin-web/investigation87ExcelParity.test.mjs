import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/InvestigationCenterPage.tsx', import.meta.url), 'utf8')

test('8.7 row 2 keeps every legacy collection field and proof-file upload', () => {
  for (const label of ['取证机构', '公证书号', '取证日期', '发票号码', '证物存放处', '证物状态', '证据文件']) {
    assert.match(source, new RegExp(label))
  }
  assert.match(source, /AutoComplete/)
  assert.match(source, /evidence_file_ids:\s*uploadedIds/)
  assert.match(source, /category", "取证文件"/)
})

test('8.7 row 3 resolves the contract from source tasks rather than a manual selector', () => {
  assert.match(source, /investigations\/clues\/case-contracts/)
  assert.match(source, /合同由线索来源调查任务自动绑定/)
  assert.match(source, /生成新案待分配案件/)
  assert.match(source, /合同由线索来源调查任务自动绑定/)
  assert.match(source, /title: "基本信息"/)
  assert.match(source, /title: "生成结果"/)
})

test('new investigation tasks bind a same-customer contract and unresolved legacy data can bind once', () => {
  assert.match(source, /name="contract_record_id"/)
  assert.match(source, /请绑定与调查客户一致的合同/)
  assert.match(source, /合同由线索来源调查任务自动绑定/)
  assert.match(source, /补充来源任务合同/)
  assert.match(source, /仅列出该客户可用合同/)
  assert.match(source, /绑定并自动带入/)
})
