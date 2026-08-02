import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractReceivablesPage.tsx', import.meta.url), 'utf8')

test('my receivables keeps the legacy default page length and page-size choices', () => {
  const listPagination = source.match(/dataSource=\{visibleContracts\}[\s\S]*?pagination=\{\{([\s\S]*?)\}\}/)

  assert.ok(listPagination, 'my-receivables table must configure pagination')
  assert.match(source, /const \[listPageSize, setListPageSize\] = useState\(10\)/)
  assert.match(listPagination[1], /pageSize:\s*listPageSize/)
  assert.match(listPagination[1], /showSizeChanger:\s*true/)
  assert.match(listPagination[1], /pageSizeOptions:\s*\[10,\s*15,\s*20,\s*50,\s*100,\s*200\]/)
  assert.match(listPagination[1], /showQuickJumper:\s*\{\s*goButton:\s*<Button size="small">GO<\/Button>\s*\}/)
})

test('my receivables renders a single-page GO control without leaking into detail routes', () => {
  const helper = source.match(/export const shouldShowMyReceivablesSinglePageJumper = \(initialView: string, rowCount: number, pageSize: number\) => ([^;]+);/)
  assert.ok(helper)
  const shouldShow = new Function('initialView', 'rowCount', 'pageSize', `return (${helper[1]});`)
  assert.equal(shouldShow('contract-receivable-mine', 0, 10), false)
  assert.equal(shouldShow('contract-receivable-mine', 1, 10), true)
  assert.equal(shouldShow('contract-receivable-mine', 11, 10), false)
  assert.equal(shouldShow('contract-receivable-detail', 1, 10), false)
  assert.match(source, /shouldShowMyReceivablesSinglePageJumper\(initialView, visibleContracts\.length, listPageSize\).*aria-label="页码"[\s\S]*?setListPage\(1\).*?>GO<\/Button>/)
})
