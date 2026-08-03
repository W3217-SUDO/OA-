import test from 'node:test'
import assert from 'node:assert/strict'
import {
  CUSTOMER_EVENT_MAX_LENGTH,
  CUSTOMER_LIST_PAGE_SIZES,
  buildCustomerActionConfirmation,
  buildCustomerActionRequest,
  buildCustomerContactListRequest,
  buildCustomerDocumentUploadFields,
  buildCustomerListParams,
  getCustomerDocumentUploadError,
  getCustomerActionMessage,
  isCustomerDetailManageable,
  normalizeCustomerContactPage,
  normalizeCustomerListPagination,
  buildCustomerDetailReturnState,
  buildCustomerEventRequest,
} from './src/customerParity.mjs'

test('customer lifecycle requests keep the four legacy state actions and trim comments', () => {
  assert.deepEqual(buildCustomerActionRequest(12, 'recycle', '  删除说明  '), {
    method: 'post', url: '/customers/12/recycle', data: { comment: '删除说明' },
  })
  assert.deepEqual(buildCustomerActionRequest('12', 'claim'), {
    method: 'post', url: '/customers/12/claim', data: { comment: '' },
  })
  assert.equal(buildCustomerActionRequest(0, 'restore'), null)
  assert.equal(buildCustomerActionRequest(12, 'merge'), null)
})

test('customer lifecycle confirmation marks destructive recycle only', () => {
  assert.deepEqual(buildCustomerActionConfirmation('recycle', '客户甲'), {
    action: 'recycle', title: '客户甲', danger: true, requiresConfirm: true,
  })
  assert.equal(buildCustomerActionConfirmation('claim', '客户甲').danger, false)
  assert.equal(buildCustomerActionConfirmation('unknown', '客户甲'), null)
})

test('customer lifecycle messages retain action-specific success and failure keys', () => {
  for (const action of ['claim', 'release', 'recycle', 'restore']) {
    assert.equal(typeof getCustomerActionMessage(action, true), 'string')
    assert.equal(typeof getCustomerActionMessage(action, false), 'string')
    assert.notEqual(getCustomerActionMessage(action, true), getCustomerActionMessage(action, false))
  }
})

test('customer list params default to legacy page one and page size fifteen', () => {
  assert.deepEqual(buildCustomerListParams({ scope: 'company' }), {
    scope: 'company', customer_name: '', customer_type: '客户', manager: '', page: 1, page_size: 15,
  })
  assert.deepEqual(normalizeCustomerListPagination(31, 0, 999), { page: 1, pageSize: 15, lastPage: 3 })
  assert.deepEqual(CUSTOMER_LIST_PAGE_SIZES, [10, 15, 20, 50, 100, 200])
})

test('shared and recent customer scopes omit the manager filter', () => {
  const params = buildCustomerListParams({ scope: 'shared', manager: 'alice', keyword: '  A  ', page: 2, pageSize: 20 })
  assert.deepEqual(params, { scope: 'shared', customer_name: 'A', customer_type: '客户', page: 2, page_size: 20 })
})

test('customer list pagination clamps invalid page and size values', () => {
  assert.deepEqual(buildCustomerListParams({ scope: 'mine', page: -2, pageSize: 13 }), {
    scope: 'mine', customer_name: '', customer_type: '客户', manager: '', page: 1, page_size: 15,
  })
})

test('contact list request preserves legacy server-side page contract', () => {
  assert.deepEqual(buildCustomerContactListRequest(7), {
    method: 'get', url: '/customers/7/contacts', params: { page: 1, page_size: 15 },
  })
  assert.deepEqual(buildCustomerContactListRequest(7, 3, 50).params, { page: 3, page_size: 50 })
  assert.equal(buildCustomerContactListRequest(0), null)
})

test('contact list response normalizes stable items, total and page context', () => {
  assert.deepEqual(normalizeCustomerContactPage({ items: [{ id: 'c1' }], total: '9', page: 2, page_size: 20 }), {
    items: [{ id: 'c1' }], total: 9, page: 2, pageSize: 20,
  })
  assert.deepEqual(normalizeCustomerContactPage({}), { items: [], total: 0, page: 1, pageSize: 15 })
})

test('customer document upload fields carry both record and legacy customer guid context', () => {
  assert.deepEqual(buildCustomerDocumentUploadFields({ customerId: 7, customerGuid: 'g/1', category: '客户资料', remark: '  说明 ', isLicense: true }), {
    record_id: '7', customer_guid: 'g/1', category: '客户资料', remark: '说明', is_license: 'true',
  })
})

test('customer document upload failures preserve no-file, empty, type and size distinctions', () => {
  assert.equal(getCustomerDocumentUploadError({ response: { status: 413 } }), '文件不能超过 20MB')
  assert.equal(getCustomerDocumentUploadError({ response: { status: 422 }, code: 'empty' }), '文件没有任何内容')
  assert.equal(getCustomerDocumentUploadError({ response: { status: 422 }, code: 'type' }), '上传文件类型不正确')
  assert.equal(getCustomerDocumentUploadError({}), '上传失败')
})

test('customer event request enforces the old 1000-character content boundary', () => {
  assert.equal(CUSTOMER_EVENT_MAX_LENGTH, 1000)
  assert.equal(buildCustomerEventRequest('guid-1', 'x'.repeat(1001)), null)
  assert.equal(buildCustomerEventRequest('guid-1', ' x '.repeat(2)).data.comment, 'x  x')
})

test('customer detail write controls follow owner, manager and admin scope', () => {
  assert.equal(isCustomerDetailManageable({ owner: 'alice', data: { customer_managers: [] } }, { username: 'alice', role: 'user' }), true)
  assert.equal(isCustomerDetailManageable({ owner: 'alice', data: { customer_managers: ['bob'] } }, { username: 'bob', role: 'user' }), true)
  assert.equal(isCustomerDetailManageable({ owner: 'alice', department: '上海', data: {} }, { username: 'bob', role: 'manager', department: '上海' }), true)
  assert.equal(isCustomerDetailManageable({ owner: 'alice', data: {} }, { username: 'bob', role: 'user' }), false)
})

test('customer return context preserves scope, filters and pager across detail navigation', () => {
  assert.deepEqual(buildCustomerDetailReturnState({ scope: 'company', page: 3, pageSize: 50, keyword: '甲', managerKeyword: 'alice' }), {
    scope: 'company', page: 3, pageSize: 50, keyword: '甲', managerKeyword: 'alice',
  })
})
