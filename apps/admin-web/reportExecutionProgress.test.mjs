import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ReportCenterPage.tsx', import.meta.url), 'utf8')

test('execution progress report 2 renders only the four legacy execution stages', () => {
  const match = source.match(/PAGE_SPECS\["reports-execution-2"\] = \{([\s\S]*?)\n\};/)

  assert.ok(match, 'report 2 needs its own page specification')
  assert.doesNotMatch(match[1], /reports-execution-1/)
  assert.deepEqual(
    [...match[1].matchAll(/\{ title: "([^"]+)"/g)].map((item) => item[1]),
    ["执行受理案件数量", "执行中止案件数量", "执行结案案件数量", "执行终本案件数量"],
  )
})

test('execution progress report 3 renders only the two legacy execution stages', () => {
  const match = source.match(/PAGE_SPECS\["reports-execution-3"\] = \{([\s\S]*?)\n\};/)

  assert.ok(match, 'report 3 needs its own page specification')
  assert.doesNotMatch(match[1], /reports-execution-1/)
  assert.deepEqual(
    [...match[1].matchAll(/\{ title: "([^"]+)"/g)].map((item) => item[1]),
    ["执行终结案件数量", "执行中止案件数量"],
  )
})
