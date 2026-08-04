import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import {
  assertCustomerMutationSuccess,
  getCustomerMutationErrorMessage,
} from "./src/customerUiBatchI17.mjs"
import { buildCustomerContactStatusRequest } from "./src/customerUiBatchI14.mjs"

const pageSource = fs.readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8")

const handlerNames = [
  "createCustomerEvent",
  "addContact",
  "updateContact",
  "deleteContact",
  "updateContactStatus",
  "addNote",
  "updateNote",
  "deleteNote",
  "uploadDocument",
  "deleteDocument",
]

const handlerSource = (name) => {
  const start = pageSource.indexOf(`const ${name} =`)
  const next = handlerNames
    .map((candidate) => pageSource.indexOf(`const ${candidate} =`, start + 1))
    .filter((position) => position >= 0)
  return pageSource.slice(start, next.length ? Math.min(...next) : pageSource.length)
}

const sourceUntilNextConst = (name) => {
  const start = pageSource.indexOf(`const ${name} =`)
  assert.ok(start >= 0, `${name} handler is present`)
  const next = pageSource.indexOf("\n  const ", start + 1)
  return pageSource.slice(start, next < 0 ? pageSource.length : next)
}

test("legacy HTTP200 mutation failure reaches the UI error message", () => {
  let failure
  try {
    assertCustomerMutationSuccess({ IsSuccess: false, Message: "联系人保存失败" })
  } catch (error) {
    failure = error
  }
  assert.equal(getCustomerMutationErrorMessage(failure, "通用失败"), "联系人保存失败")
  assert.throws(() => assertCustomerMutationSuccess({ ok: false, detail: "服务端拒绝" }), /服务端拒绝/)
})

test("every I18 handler asserts response before success side effects", () => {
  let failure
  try {
    assertCustomerMutationSuccess({ IsSuccess: false, Message: "旧端业务失败" })
  } catch (error) {
    failure = error
  }
  for (const name of handlerNames) {
    const source = handlerSource(name)
    assert.ok(source, `${name} handler is present`)
    const assertion = source.indexOf("assertCustomerMutationSuccess(response?.data)")
    assert.ok(assertion >= 0, `${name} validates response.data`)
    const success = source.indexOf("message.success")
    if (success >= 0) assert.ok(assertion < success, `${name} validates before success UI`)
    assert.match(source, /catch \(error: any\)/, `${name} keeps a failure path`)
    assert.match(source, /getCustomerMutationErrorMessage\(error/, `${name} preserves legacy Message in catch`)
    assert.equal(getCustomerMutationErrorMessage(failure, `${name} fallback`), "旧端业务失败")
  }
})

test("204 and ordinary JSON mutation responses remain successful", () => {
  assert.doesNotThrow(() => assertCustomerMutationSuccess(undefined))
  assert.deepEqual(assertCustomerMutationSuccess({ id: 42, status: "正常" }), { id: 42, status: "正常" })
  assert.deepEqual(assertCustomerMutationSuccess({ data: { id: 42 } }), { data: { id: 42 } })
})

test("contact default and active status requests keep exact runtime payloads", () => {
  assert.deepEqual(
    buildCustomerContactStatusRequest(7, "c-1", "primary"),
    { method: "patch", url: "/customers/7/contacts/c-1/status", data: { is_primary: true } },
  )
  assert.deepEqual(
    buildCustomerContactStatusRequest(7, "c-1", "active"),
    { method: "patch", url: "/customers/7/contacts/c-1/status", data: { is_valid: true } },
  )
  assert.deepEqual(
    buildCustomerContactStatusRequest(7, "c-1", "inactive"),
    { method: "patch", url: "/customers/7/contacts/c-1/status", data: { is_valid: false } },
  )
})

test("customer peripheral mutations preserve legacy failure envelopes before success UI", () => {
  for (const name of ["uploadContactPhoto", "recycleCustomer"]) {
    const source = sourceUntilNextConst(name)
    const assertion = source.indexOf("assertCustomerMutationSuccess(response?.data)")
    assert.ok(assertion >= 0, `${name} validates response.data`)
    assert.ok(assertion < source.indexOf("message.success"), `${name} validates before success UI`)
    assert.match(source, /catch \(error: any\)/, `${name} keeps a failure path`)
    assert.match(source, /getCustomerMutationErrorMessage(?:I17)?\(error/, `${name} preserves legacy Message in catch`)
  }
})

test("customer detail loaders preserve legacy response messages", () => {
  for (const name of ["loadContactPage", "openDetail"]) {
    const source = sourceUntilNextConst(name)
    assert.match(source, /catch \(error: any\)/, `${name} keeps a failure path`)
    assert.match(source, /getCustomerResponseMessage\(error/, `${name} consumes legacy response Message`)
  }
})
