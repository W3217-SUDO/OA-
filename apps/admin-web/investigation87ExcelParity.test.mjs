import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/InvestigationCenterPage.tsx', import.meta.url), 'utf8')
const contractSource = await readFile(new URL('./src/ContractCenterPage.tsx', import.meta.url), 'utf8')
const regionSource = await readFile(new URL('./src/investigationRegionOptions.mjs', import.meta.url), 'utf8')

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

test('new investigation tasks visibly carry the nationwide authorization scope', () => {
  assert.match(contractSource, /label="授权范围"/)
  assert.match(contractSource, /options=\{\["全国", "区域"\]/)
  assert.match(contractSource, /value === "全国" \? "全国"/)
  assert.match(contractSource, /授权区域：全国/)
})

test('regional investigation scope uses a province-expanding city dialog with nationwide city data', () => {
  assert.match(contractSource, /title="选择城市"/)
  assert.match(contractSource, /全选/)
  assert.match(contractSource, /清空/)
  assert.match(contractSource, /Checkbox\.Group/)
  assert.match(contractSource, /expandedInvestigationProvinces/)
  assert.match(contractSource, /INVESTIGATION_REGION_GROUPS/)
  assert.match(contractSource, /cities\.map\(city/)
  assert.match(regionSource, /黑龙江省/)
  assert.match(regionSource, /哈尔滨市/)
  assert.match(regionSource, /广东省/)
  assert.match(regionSource, /广州市/)
  assert.match(regionSource, /新疆维吾尔自治区/)
  assert.match(regionSource, /乌鲁木齐市/)
  assert.doesNotMatch(regionSource, /"province":\s*"\?+"/)
})
