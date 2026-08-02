import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractReceivablesPage.tsx', import.meta.url), 'utf8')

test('receivables detail keeps the legacy 10-row pagination controls', () => {
  const pageSizes = source.match(/export const receivablesDetailPageSizes = (\[[^;]+\]);/)

  assert.ok(pageSizes, 'detail pagination must expose the legacy page-size choices')
  const sizes = new Function(`return (${pageSizes[1]})`)()
  assert.deepEqual(sizes, [10, 15, 20, 50, 100, 200])
  assert.match(source, /dataSource=\{detailRows\}[\s\S]*?pagination=\{\{ current: detailPage, pageSize: detailPageSize, showSizeChanger: true, pageSizeOptions: receivablesDetailPageSizes, showQuickJumper: \{ goButton: <Button size="small">GO<\/Button> \}/)
  assert.match(source, /shouldShowReceivablesDetailSinglePageJumper\(detailRows\.length, detailPageSize\) && <Space[\s\S]*?<Button size="small" onClick=\{\(\) => setDetailPage\(1\)\}>GO<\/Button>/)
})
