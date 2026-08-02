import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractReceivablesPage.tsx', import.meta.url), 'utf8')

test('receivables case links resolve exact case detail route and return to receivable detail', () => {
  assert.match(source, /export const buildReceivableCaseDetailRoute = \(/, 'case links need an exact detail route helper')
  assert.match(source, /sunhold:case-list-return/, 'case links need a return context')
  assert.match(source, /buildReceivableCaseDetailRoute\([^)]*\)/, 'case links must navigate to the resolved case detail route')
  assert.match(source, /className="receivable-case-link"/, 'case links need a hit-test-safe class')
  assert.match(source, /maxWidth:\s*"100%"/, 'case links must stay within the table cell hit area')
  assert.match(source, /未找到关联案件或当前账号无权查看/, 'missing case targets must show a user-facing warning')
  assert.match(source, /关联案件加载失败/, 'case lookup failures must show a user-facing error')
})
