import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import { assertCustomerMutationSuccess, getCustomerMutationErrorMessage } from "./src/customerUiBatchI17.mjs"

const pageSource = fs.readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8")

test("legacy mutation failure envelopes throw their server message", () => {
  let failure
  try {
    assertCustomerMutationSuccess({ IsSuccess: false, Message: "保存失败" })
  } catch (error) {
    failure = error
  }
  assert.equal(getCustomerMutationErrorMessage(failure, "fallback"), "保存失败")
  assert.throws(() => assertCustomerMutationSuccess({ isSuccess: false, message: "共享失败" }), /共享失败/)
  assert.throws(() => assertCustomerMutationSuccess({ ok: false, detail: "无权限" }), /无权限/)
  assert.equal(getCustomerMutationErrorMessage({ response: { data: { Message: "服务端失败" } } }, "fallback"), "服务端失败")
})

test("successful local mutation responses stay successful without a legacy envelope", () => {
  assert.deepEqual(assertCustomerMutationSuccess({ id: 1, title: "客户" }), { id: 1, title: "客户" })
  assert.deepEqual(assertCustomerMutationSuccess({ data: { items: [] } }), { data: { items: [] } })
  assert.doesNotThrow(() => assertCustomerMutationSuccess(undefined))
})

test("customer mutation handlers validate every existing response before success UI", () => {
  assert.ok((pageSource.match(/assertCustomerMutationSuccess\(/g) || []).length >= 9)
  assert.match(pageSource, /getCustomerMutationErrorMessage\s+as\s+getCustomerMutationErrorMessageI17/)
  const handlerNames = [
    "save",
    "assignCustomer",
    "action",
    "share",
    "openPortal",
    "closePortal",
  ]
  for (const [index, name] of handlerNames.entries()) {
    const start = pageSource.indexOf(`const ${name} =`)
    const nextStarts = handlerNames
      .slice(index + 1)
      .map((nextName) => pageSource.indexOf(`const ${nextName} =`, start + 1))
      .filter((position) => position >= 0)
    const end = nextStarts.length ? Math.min(...nextStarts) : pageSource.length
    const handlerSource = pageSource.slice(start, end)
    assert.ok(start >= 0, `${name} handler is present`)
    assert.match(handlerSource, /assertCustomerMutationSuccess\(response\?\.data\)/, `${name} validates response`)
    assert.match(handlerSource, /getCustomerMutationErrorMessage(?:I17)?\(error/, `${name} keeps legacy server message in catch`)
  }
  for (const endpoint of [
    "/customers/${assigning.id}/managers",
    "/customers/${sharing.id}/share",
    "/portal/open",
    "/portal/close",
  ]) assert.match(pageSource, new RegExp(endpoint.replace(/[${}]/g, "\\$&")))
})
