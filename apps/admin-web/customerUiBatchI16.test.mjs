import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import {
  normalizeCustomerCollectionItems,
  normalizeCustomerEventItems,
  normalizeCustomerAttachmentItems,
  normalizeCustomerSharedObjectItems,
  normalizeCustomerHistoryItems,
  assertCustomerCollectionSuccess,
  getCustomerResponseMessage,
} from "./src/customerUiBatchI16.mjs"

const pageSource = fs.readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8")

test("legacy customer event array and PascalCase fields render in local shape", () => {
  const items = normalizeCustomerEventItems({ Data: [{ Id: 7, Content: "电话沟通", Operator: "alice", OperateTime: "2026-08-01" }] })
  assert.deepEqual(items, [{ Id: 7, Content: "电话沟通", Operator: "alice", OperateTime: "2026-08-01", id: 7, content: "电话沟通", operator: "alice", created_at: "2026-08-01" }])
})

test("local customer event items remain intact while aliases are normalized", () => {
  const items = normalizeCustomerEventItems({ data: { items: [{ id: "e1", content: "跟进", operator: "bob", created_at: "2026-08-02", action: "note" }] } })
  assert.equal(items[0].id, "e1")
  assert.equal(items[0].content, "跟进")
  assert.equal(items[0].operator, "bob")
  assert.equal(items[0].created_at, "2026-08-02")
  assert.equal(items[0].action, "note")
})

test("malformed event payload becomes a stable empty state", () => {
  assert.deepEqual(normalizeCustomerEventItems({ data: { items: null } }), [])
  assert.deepEqual(normalizeCustomerEventItems(null), [])
})

test("legacy customer file array maps PascalCase identity and date fields", () => {
  const items = normalizeCustomerAttachmentItems({ Data: [{ CustomerFileId: 3, FileName: "license.pdf", FileDate: "2026-07-30", FileUploader: "alice" }] })
  assert.equal(items[0].id, 3)
  assert.equal(items[0].original_name, "license.pdf")
  assert.equal(items[0].document_date, "2026-07-30")
  assert.equal(items[0].uploader, "alice")
})

test("local customer attachment items preserve document_date before created_at", () => {
  const items = normalizeCustomerAttachmentItems({ data: { items: [{ id: 4, original_name: "x.pdf", document_date: "2026-08-01", created_at: "2026-08-02" }] } })
  assert.deepEqual(items[0], { id: 4, original_name: "x.pdf", document_date: "2026-08-01", created_at: "2026-08-02" })
})

test("legacy shared-object array is normalized, trimmed and de-duplicated", () => {
  assert.deepEqual(normalizeCustomerSharedObjectItems({ Data: [{ StaffName: " alice " }, { username: "alice" }, { StaffName: "bob" }] }), ["alice", "bob"])
})

test("local shared-object Items payload is accepted", () => {
  assert.deepEqual(normalizeCustomerSharedObjectItems({ data: { Items: [{ staff_name: "alice" }, " bob "] } }), ["alice", "bob"])
})

test("legacy history array and local history items share one renderer shape", () => {
  assert.deepEqual(normalizeCustomerHistoryItems({ Data: [{ Id: 1, Action: "保存", Operator: "alice", Comment: "ok", CreatedAt: "2026-08-01" }] }), [{ Id: 1, Action: "保存", Operator: "alice", Comment: "ok", CreatedAt: "2026-08-01", id: 1, action: "保存", operator: "alice", comment: "ok", created_at: "2026-08-01" }])
  assert.deepEqual(normalizeCustomerHistoryItems({ data: { items: [] } }), [])
})

test("collection adapter accepts axios, legacy and local envelopes", () => {
  assert.deepEqual(normalizeCustomerCollectionItems({ data: { Data: [{ id: 1 }] } }), [{ id: 1 }])
  assert.deepEqual(normalizeCustomerCollectionItems({ data: [{ id: 2 }] }), [{ id: 2 }])
  assert.deepEqual(normalizeCustomerCollectionItems({ items: [{ id: 3 }] }), [{ id: 3 }])
})

test("collection adapter never leaks malformed scalar values into tables", () => {
  assert.deepEqual(normalizeCustomerCollectionItems({ data: { items: "not-an-array" } }), [])
  assert.deepEqual(normalizeCustomerCollectionItems(42), [])
})

test("customer detail consumes adapters for every legacy collection response", () => {
  for (const helper of [
    "normalizeCustomerCollectionItems",
    "normalizeCustomerAttachmentItems",
    "normalizeCustomerEventItems",
    "normalizeCustomerHistoryItems",
    "normalizeCustomerSharedObjectItems",
  ]) assert.match(pageSource, new RegExp(`${helper}\\(`))
})

test("legacy HTTP200 failure envelope preserves Message instead of becoming empty", () => {
  assert.throws(() => normalizeCustomerEventItems({ IsSuccess: false, Message: "旧事项查询失败" }), /旧事项查询失败/)
  assert.throws(() => normalizeCustomerAttachmentItems({ isSuccess: false, message: "旧文档查询失败" }), /旧文档查询失败/)
  assert.throws(() => normalizeCustomerSharedObjectItems({ ok: false, detail: "共享对象无权限" }), /共享对象无权限/)
  assert.equal(getCustomerResponseMessage({ response: { data: { Message: "服务端文案" } } }, "fallback"), "服务端文案")
})

test("missing failure text uses real UTF-8 customer fallback and no mojibake", () => {
  assert.equal(getCustomerResponseMessage({ response: { data: {} } }), "客户数据加载失败")
  assert.equal(getCustomerResponseMessage({}), "客户数据加载失败")
  const helperSource = fs.readFileSync(new URL("./src/customerUiBatchI16.mjs", import.meta.url), "utf8")
  assert.equal((helperSource.match(/客户数据加载失败/g) || []).length, 2)
  assert.doesNotMatch(helperSource, /瀹㈡埛鏁版嵁鍔犺浇澶辫触/)
})

test("successful empty legacy and local envelopes remain normal empty states", () => {
  assert.deepEqual(normalizeCustomerEventItems({ IsSuccess: true, Data: [] }), [])
  assert.deepEqual(normalizeCustomerAttachmentItems({ data: { items: [] } }), [])
  assert.deepEqual(normalizeCustomerSharedObjectItems({ ok: true, items: [] }), [])
  assert.doesNotThrow(() => assertCustomerCollectionSuccess({ data: { items: [] } }))
})

test("page catches each detail collection independently and keeps record target fallback", () => {
  assert.match(pageSource, /recordErrorMessage/)
  assert.match(pageSource, /attachmentErrorMessage/)
  assert.match(pageSource, /normalizeCustomerEventItems\(customerEventRes\.data\)/)
  assert.match(pageSource, /normalizeCustomerAttachmentItems\(fileRes\.data\)/)
  assert.match(pageSource, /normalizeCustomerSharedObjectItems\(sharedObjectsRes\.data\)/)
  assert.match(pageSource, /normalizeCustomerHistoryItems\(historyRes\.data\)/)
  assert.match(pageSource, /\|\| target/)
})
