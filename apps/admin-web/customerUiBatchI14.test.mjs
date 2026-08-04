import test from "node:test"
import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"
import {
  OLD_CUSTOMER_EMAIL_PATTERN,
  normalizeCustomerRecipients,
  buildCustomerShareRequest,
  normalizeCustomerManager,
  buildCustomerManagerRequest,
  matchesDirectoryOption,
  validateCustomerUploadFile,
  validateCustomerPhotoFile,
  buildCustomerContactStatusRequest,
  getCustomerPermissionMessage,
  getCustomerMutationErrorMessage,
} from "./src/customerUiBatchI14.mjs"

test("old CRM email rule is applied to customer and default-contact values", () => {
  const valid = ["a@example.com", "user-name_tag@example.com", "a.b@foo-bar.example"]
  const invalid = ["a@", "a b@example.com", "@example.com", "a@example"]
  for (const value of valid) assert.match(value, OLD_CUSTOMER_EMAIL_PATTERN)
  for (const value of invalid) assert.doesNotMatch(value, OLD_CUSTOMER_EMAIL_PATTERN)
})

test("share recipients trim, remove blanks, dedupe, and preserve order", () => {
  assert.deepEqual(normalizeCustomerRecipients([" alice ", "", "bob", "alice", "  ", "bob "]), ["alice", "bob"])
  assert.deepEqual(normalizeCustomerRecipients(" alice, bob "), ["alice", "bob"])
})

test("share request refuses empty recipients and emits backend payload", () => {
  assert.equal(buildCustomerShareRequest(12, [" ", ""], "x"), null)
  assert.deepEqual(buildCustomerShareRequest(12, [" alice ", "alice"], " note "), {
    method: "post",
    url: "/customers/12/share",
    data: { recipients: ["alice"], comment: "note" },
  })
})

test("manager selection normalizes one username and rejects stale blank labels", () => {
  assert.equal(normalizeCustomerManager("  alice  "), "alice")
  assert.equal(normalizeCustomerManager("  "), "")
  assert.deepEqual(buildCustomerManagerRequest(12, " alice "), {
    method: "put",
    url: "/customers/12/managers",
    data: { managers: ["alice"] },
  })
  assert.equal(buildCustomerManagerRequest(12, ""), null)
})

test("directory autocomplete matches both account and display name", async () => {
  assert.equal(matchesDirectoryOption("zhang", { value: "zhangsan", label: "张三（zhangsan）" }), true)
  assert.equal(matchesDirectoryOption("张三", { value: "zhangsan", label: "张三（zhangsan）" }), true)
  assert.equal(matchesDirectoryOption("lisi", { value: "zhangsan", label: "张三（zhangsan）" }), false)
  const page = await readFile(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8")
  assert.equal((page.match(/filterOption=\{matchesDirectoryOption\}/g) || []).length, 4)
})

test("document and contact photo preflight enforce old upload constraints", () => {
  assert.deepEqual(validateCustomerUploadFile({ name: "x.pdf", size: 1 }), { ok: true })
  assert.equal(validateCustomerUploadFile(null).code, "empty")
  assert.equal(validateCustomerUploadFile({ name: "x.pdf", size: 0 }).code, "empty")
  assert.equal(validateCustomerUploadFile({ name: "x.pdf", size: 20 * 1024 * 1024 + 1 }).code, "size")
  assert.equal(validateCustomerUploadFile({ name: "x.exe", size: 1 }).code, "type")
  assert.deepEqual(validateCustomerPhotoFile({ name: "x.JPG", size: 1 }), { ok: true })
  assert.equal(validateCustomerPhotoFile({ name: "x.jpg", size: 0 }).code, "empty")
  assert.equal(validateCustomerPhotoFile({ name: "x.pdf", size: 1 }).code, "type")
})

test("page wires zero-byte upload codes to explicit empty-file feedback", async () => {
  const page = await readFile(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8")
  assert.match(page, /validation\.code === "empty" \? "文件没有任何内容"/)
  assert.match(page, /validation\.code === "empty" \? "照片文件为空"/)
  assert.match(page, /validateCustomerUploadFile\(documentFile\)/)
  assert.match(page, /validateCustomerPhotoFile\(option\.file\)/)
})

test("contact status request supports primary, active and inactive state transitions", () => {
  assert.deepEqual(buildCustomerContactStatusRequest(5, "c1", "inactive"), {
    method: "patch",
    url: "/customers/5/contacts/c1/status",
    data: { is_valid: false },
  })
  assert.deepEqual(buildCustomerContactStatusRequest(5, "c1", "active"), {
    method: "patch",
    url: "/customers/5/contacts/c1/status",
    data: { is_valid: true },
  })
})

test("permission and mutation failures preserve explicit backend detail", () => {
  assert.equal(getCustomerPermissionMessage({ response: { status: 403 } }), "无权限执行该客户操作")
  assert.equal(getCustomerPermissionMessage({ response: { status: 404 } }), "")
  assert.equal(getCustomerMutationErrorMessage({ response: { status: 403, data: { detail: "forbidden" } } }, "fallback"), "forbidden")
  assert.equal(getCustomerMutationErrorMessage({ response: { status: 403 } }, "fallback"), "无权限执行该客户操作")
  assert.equal(getCustomerMutationErrorMessage({}, "fallback"), "fallback")
})
