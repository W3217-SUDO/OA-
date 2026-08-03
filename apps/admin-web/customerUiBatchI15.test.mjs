import test from "node:test"
import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"
import {
  CUSTOMER_CONTACT_FORM_DEFAULTS,
  CUSTOMER_DOCUMENT_FORM_DEFAULTS,
  getCustomerAttachmentDate,
  canDeleteCustomerAttachment,
} from "./src/customerUiBatchI15.mjs"
import { getCustomerMutationErrorMessage } from "./src/customerUiBatchI14.mjs"

test("customer contact and document forms expose old defaults", () => {
  assert.deepEqual(CUSTOMER_CONTACT_FORM_DEFAULTS, {
    contact_status: "正常联系",
    is_valid: true,
    is_primary: false,
    remark: "",
  })
  assert.deepEqual(CUSTOMER_DOCUMENT_FORM_DEFAULTS, {
    category: "客户资料",
    remark: "",
  })
})

test("attachment detail uses server document date without client-side pagination", () => {
  assert.equal(getCustomerAttachmentDate({ document_date: "2026-08-02", created_at: "2026-08-03" }), "2026-08-02")
  assert.equal(getCustomerAttachmentDate({ created_at: "2026-08-03" }), "2026-08-03")
  assert.equal(getCustomerAttachmentDate({}), "")
  assert.equal(canDeleteCustomerAttachment(true), true)
  assert.equal(canDeleteCustomerAttachment(false), false)
})

test("customer page wires metadata, detail date, permission and inactive action", async () => {
  const page = await readFile(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8")
  assert.match(page, /name="remark"/)
  assert.match(page, /getCustomerAttachmentDate\(/)
  assert.equal((page.match(/type="file"/g) || []).length, 2)
  assert.equal((page.match(/accept="\.pdf,\.doc,\.docx,\.xls,\.xlsx,\.ppt,\.pptx,\.txt,\.png,\.jpg,\.jpeg,\.zip,\.rar"/g) || []).length, 2)
  assert.equal((page.match(/getCustomerAttachmentDate\((?:r|row)\)/g) || []).length, 3)
  assert.equal((page.match(/canDeleteCustomerAttachment\(canManageCurrentCustomer\)/g) || []).length, 3)
  assert.doesNotMatch(page, /文档日期"[,}]\s*dataIndex[:=]\s*["']created_at/)
  assert.match(page, /updateContactStatus\(row,"inactive"\)/)
  assert.match(page, /getCustomerMutationErrorMessage\(error/)
  assert.equal(getCustomerMutationErrorMessage({ response: { status: 403 } }, "fallback"), "无权限执行该客户操作")
  assert.ok((page.match(/getCustomerMutationErrorMessage\(error/g) || []).length >= 10)
})
