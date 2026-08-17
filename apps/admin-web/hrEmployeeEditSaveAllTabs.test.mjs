import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/HrCenterPage.tsx', import.meta.url), 'utf8')

test('employee edit keeps the basic form mounted while saving from another tab', () => {
  assert.match(source, /key:'basic',label:'基本信息',children:basicNode,forceRender:true,destroyOnHidden:false/)
  assert.match(source, /const openEmployeeEdit=[\s\S]*?setDetailTab\('basic'\)/)
})

test('save-all returns to basic information when validation fails', () => {
  assert.match(source, /validateFields\(\)\}catch\(error:any\)\{if\(error\?\.errorFields\)\{setDetailTab\('basic'\);message\.error\('请先完善基本信息中的必填项'\)/)
})
