import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/SystemCenterPage.tsx', import.meta.url), 'utf8')

test('system parameter table defaults to 15 rows without fixing its page size', () => {
  const parameterPagination = source.match(/dataSource=\{visibleParameters\}[\s\S]*?pagination=\{\{([\s\S]*?)\}\}/)

  assert.ok(parameterPagination)
  assert.match(parameterPagination[1], /defaultPageSize: 15/)
  assert.match(parameterPagination[1], /showSizeChanger: true/)
  assert.match(parameterPagination[1], /pageSizeOptions: \["10", "15", "20", "50", "100", "200"\]/)
  assert.doesNotMatch(parameterPagination[1], /\bpageSize\s*:/)
})
