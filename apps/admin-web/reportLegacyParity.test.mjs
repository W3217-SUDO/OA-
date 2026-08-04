import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ReportCenterPage.tsx', import.meta.url), 'utf8')

const assignedSpec = (key) => {
  const match = source.match(new RegExp(`PAGE_SPECS\\[\\"${key}\\"\\] = \\{([\\s\\S]*?)\\n\\};`))
  assert.ok(match, `${key} needs its own page specification`)
  return match[1]
}

const inlineSpec = (key) => {
  const match = source.match(new RegExp(`\\"${key}\\": \\{([\\s\\S]*?)\\n  \\},`))
  assert.ok(match, `${key} needs an inline page specification`)
  return match[1]
}

const titles = (key) => {
  const block = key === 'reports-execution-1' ? inlineSpec(key) : assignedSpec(key)
  return [...block.matchAll(/\{ title: "([^"]+)"/g)].map((item) => item[1])
}

test('execution progress report 1 keeps only the four legacy first-stage charts', () => {
  assert.deepEqual(titles('reports-execution-1'), [
    '一审待执行案件数量',
    '二审待执行案件数量',
    '准备材料案件数量',
    '提交法院案件数量',
  ])
})

test('execution progress report 1 excludes charts owned by stages 2 and 3', () => {
  const firstStage = titles('reports-execution-1')
  for (const title of ['执行受理案件数量', '执行中止案件数量', '执行结案案件数量', '执行终本案件数量', '执行终结案件数量']) {
    assert.ok(!firstStage.includes(title), `report 1 should not include ${title}`)
  }
})

test('every legacy execution chart renders only the first 20 data points', () => {
  const allTitles = ['reports-execution-1', 'reports-execution-2', 'reports-execution-3'].flatMap(titles)
  assert.equal(allTitles.length, 10)
  assert.equal((source.match(/limit: 20/g) || []).length, 10)
  assert.match(source, /chartItems = spec\.limit \? items\.slice\(0, spec\.limit\) : items/)
})

test('report large screen export rotates the four legacy views every 30 seconds', () => {
  assert.match(source, /export function ReportLargeScreenPage/)
  assert.match(source, /30_000/)
  const views = source.match(/const largeScreenViews = \[([^\]]+)\]/)
  assert.ok(views, 'large screen view list should exist')
  for (const key of ['reports-refund', 'reports-execution-1', 'reports-execution-2', 'reports-execution-3']) {
    assert.ok(views[1].includes(key), `large screen should include ${key}`)
  }
})
