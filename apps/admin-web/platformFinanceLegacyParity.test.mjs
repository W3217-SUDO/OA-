import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/PlatformFinancePage.tsx', import.meta.url), 'utf8')

test('platform finance query route uses the legacy receipt query kind', () => {
  assert.match(source, /"platform-finance-overview-query": \{ title: "回款查询", kind: "receipt-query" \}/)
})

test('receipt query page exposes the legacy query fields', () => {
  const match = source.match(/const receiptQueryFields: QueryField\[\] = \[([\s\S]*?)\n\];/)
  assert.ok(match, 'receiptQueryFields should exist')
  for (const label of ['回款流水号', '客户名称', '回款日期', '回款单位', '回款方式', '合同编号', '销售代表']) {
    assert.match(match[1], new RegExp(`label: "${label}"`))
  }
})

test('receipt query page exposes the legacy AR payment columns', () => {
  const match = source.match(/const receiptQueryColumns: TableColumnsType<EmptyRow> = \[([\s\S]*?)\n\];/)
  assert.ok(match, 'receiptQueryColumns should exist')
  assert.match(match[1], /operationColumn,/)
  for (const title of ['回款流水号', '合同编号', '客户名称', '回款单位', '销售代表', '回款日期', '回款金额', '官费', '代理费', '其他费用', '回款方式', '银行单据号']) {
    assert.match(match[1], new RegExp(`column\\("${title}"`))
  }
})

test('invoice list keeps the legacy invoice number label and remark column', () => {
  const match = source.match(/const invoiceColumns: TableColumnsType<EmptyRow> = \[([\s\S]*?)\n\];/)
  assert.ok(match, 'invoiceColumns should exist')
  assert.match(match[1], /column\("发票编号"/)
  assert.match(match[1], /column\("备注", 180\)/)
})

test('invoice list supports legacy export-all and export-selected actions', () => {
  assert.match(source, /showSelection = \["receipt", "invoice"/)
  assert.match(source, /导出全部/)
  assert.match(source, /导出选中/)
  assert.match(source, /const exportCsv = \(rows = filteredRows\)/)
})
