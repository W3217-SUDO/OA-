import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/SystemCenterPage.tsx', import.meta.url), 'utf8')
const configStart = source.indexOf('} else if (initialView === "system-management-config")')
const configEnd = source.indexOf('} else if (initialView === "system-users")', configStart)
const configBlock = source.slice(configStart, configEnd)

test('system config keeps legacy pagination and quick-jumper controls', () => {
  assert.match(configBlock, /defaultPageSize: 15/)
  assert.match(configBlock, /showSizeChanger: true/)
  assert.match(configBlock, /pageSizeOptions: \["10", "15", "20", "50", "100", "200"\]/)
  assert.match(configBlock, /showQuickJumper: true/)
  assert.match(configBlock, /showTotal: \(total\) => `共有\$\{total\}条`/)
  assert.doesNotMatch(configBlock, /pagination=\{false\}/)
})

test('system config remains read-only like legacy page', () => {
  assert.doesNotMatch(configBlock, /Button|Popconfirm|onClick|Form/) 
  assert.match(configBlock, /dataSource=\{configs\}/)
})
