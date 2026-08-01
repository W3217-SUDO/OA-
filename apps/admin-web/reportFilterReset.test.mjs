import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ReportCenterPage.tsx', import.meta.url), 'utf8')

test('report filters expose a reset action that reloads unfiltered analytics', () => {
  assert.match(source, /form\.resetFields\(\)/)
  assert.match(source, /<Button onClick=\{\(\)=>\{form\.resetFields\(\); onQuery\(\{\}\)\}\}>重置<\/Button>/)
})
