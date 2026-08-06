import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/InvestigationCenterPage.tsx', import.meta.url), 'utf8')

test('clue edit modal exposes every backend-editable investigation data field', () => {
  assert.match(source, /editTarget\?\.module==='clue'&&<>[\s\S]*name="infringement_method"[\s\S]*name="platform"[\s\S]*name="product"[\s\S]*name="source"[\s\S]*name="address"/)
})

test('clue save sends the backend-editable investigation data fields', () => {
  assert.match(source, /data:\{region:v\.region\|\|''[\s\S]*address:v\.address\|\|''[\s\S]*infringement_method:v\.infringement_method\|\|''/)
  assert.match(source, /platform:v\.platform\|\|''[\s\S]*product:v\.product\|\|''[\s\S]*source:v\.source\|\|''/)
})

test('clue edits from every review stage re-enter pending review', () => {
  assert.match(source, /const resubmit=editTarget\.module==='clue'&&!\['草稿','已驳回'\]\.includes\(editTarget\.status\)/)
  assert.match(source, /\?\{status:'待审批'\}:\{\}/)
  assert.match(source, /线索已修改并重新进入待审核/)
})

test('investigation task list does not offer a second parent-task creation entry', () => {
  assert.doesNotMatch(source, /investigation-task-published'\]:\['查询','刷新','新建调查任务'/)
  assert.doesNotMatch(source, /investigation-task-mine'\]:\['查询','刷新','新建调查任务'/)
})

test('clue create modal keeps legacy source, store and subject fields', () => {
  assert.match(source, /name="infringement_method"[\s\S]*name="store_url"[\s\S]*name="shop_id"[\s\S]*name="address"[\s\S]*name="investigated_at"[\s\S]*name="producer"[\s\S]*name="indictee"[\s\S]*name="investigation_assistant"/)
})

test('clue create payload keeps legacy source, store and subject fields', () => {
  for (const key of ['infringement_method', 'store_url', 'shop_id', 'address', 'producer', 'indictee', 'investigation_assistant']) {
    assert.match(source, new RegExp(key + ':values\\.' + key + '\\|\\|\'\''))
  }
})

test('clue detail modal renders the legacy clue evidence and subject sections', () => {
  assert.match(source, /label:'侵权方式'[\s\S]*label:'店铺链接'[\s\S]*label:'生产商'[\s\S]*label:'主体信息'[\s\S]*label:'调查辅助'[\s\S]*label:'取证机构'[\s\S]*label:'证物状态'/)
})

test('customer review modal shows the previous auditor and opinion', () => {
  assert.match(source, /clueReviewing\?\.status==='待客户审核'[\s\S]*上一级审核员[\s\S]*上一级审核意见/)
})
