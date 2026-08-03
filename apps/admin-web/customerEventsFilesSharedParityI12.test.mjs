import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildCustomerEventRequest,
  buildCustomerEventListPath,
  buildCustomerFileListPath,
  buildCustomerFileDownloadPath,
  getCustomerGuid,
} from './src/customerParity.mjs'
import { readFile } from 'node:fs/promises'

const pageSource = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

test('customer guid compatibility builds event and file routes without unsafe fallbacks', () => {
  assert.equal(getCustomerGuid({ customer_guid: 'cg-1' }), 'cg-1')
  assert.equal(getCustomerGuid({ data: { customer_guid: 'cg-2' } }), 'cg-2')
  assert.equal(getCustomerGuid({ customer_guid: '', data: { customer_guid: 'cg-3' } }), 'cg-3')
  assert.equal(getCustomerGuid({ data: {} }), '')
  assert.equal(buildCustomerEventListPath('cg-1'), '/customers/guid/cg-1/events')
  assert.deepEqual(buildCustomerEventRequest('cg-1', '  注意事项  '), {
    method: 'post',
    url: '/customers/guid/cg-1/events',
    data: { action: '客户注意事项', comment: '注意事项' },
  })
  assert.equal(buildCustomerEventRequest('cg-1', '   '), null)
  assert.equal(buildCustomerEventRequest('', '内容'), null)
  assert.equal(buildCustomerFileListPath('cg-1'), '/customers/guid/cg-1/files')
  assert.equal(buildCustomerFileDownloadPath('cg-1', 8), '/customers/guid/cg-1/files/8/download')
  assert.equal(buildCustomerFileDownloadPath('', 8), null)
})

test('customer detail consumes guid events, guid files, and shared-object projections', () => {
  assert.match(pageSource, /buildCustomerEventRequest/)
  assert.match(pageSource, /buildCustomerEventListPath/)
  assert.match(pageSource, /buildCustomerFileListPath/)
  assert.match(pageSource, /buildCustomerFileDownloadPath/)
  assert.match(pageSource, /shared-objects/)
  assert.match(pageSource, /customer-events/)
  assert.match(pageSource, /customerEventError/)
  assert.match(pageSource, /sharedObjectsError/)
  assert.match(pageSource, /客户注意事项/)
})

test('customer detail keeps empty/error states and permission-gated event creation visible', () => {
  assert.match(pageSource, /暂无客户注意事项/)
  assert.match(pageSource, /客户注意事项加载失败/)
  assert.match(pageSource, /共享对象加载失败/)
  assert.match(pageSource, /createCustomerEvent/)
  assert.match(pageSource, /canManageCurrentCustomer/)
  assert.match(pageSource, /customerEventForm/)
})
