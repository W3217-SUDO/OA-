import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/App.tsx', import.meta.url), 'utf8')

test('事项记录正式入口可达且不改变公司任务路由', () => {
  assert.match(source, /lazyWithVersionRecovery\("business", \(\) => import\("\.\/BusinessPage"\)\)/)
  assert.match(source, /key: "affairs-records"/)
  assert.match(source, /route === "affairs-records"[\s\S]*<BusinessPage module="task"/)
  assert.match(source, /route\.startsWith\("task-"\)[\s\S]*<TaskCenterPage initialView=\{active\}/)
})
