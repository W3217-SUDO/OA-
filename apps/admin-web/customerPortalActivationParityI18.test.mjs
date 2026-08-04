import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"

const customerCenterSource = fs.readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8")
const customerPortalSource = fs.readFileSync(new URL("./src/CustomerPortalPage.tsx", import.meta.url), "utf8")

test("I18 customer-service opening gives both login account and one-time activation code", () => {
  assert.match(customerCenterSource, /\/customers\/\$\{customer\.id\}\/portal\/open/)
  assert.match(customerCenterSource, /portalResult\?\.account/)
  assert.match(customerCenterSource, /portalResult\?\.activation_code/)
  assert.ok(customerCenterSource.includes("服务账号"))
  assert.ok(customerCenterSource.includes("一次性激活码"))
  assert.ok(customerCenterSource.includes("客户首次登录时需用二者设置密码"))
})

test("I18 customer portal has activation flow before password login", () => {
  assert.match(customerPortalSource, /\/customer-portal\/activate/)
  assert.match(customerPortalSource, /\/customer-portal\/overview/)
  assert.match(customerPortalSource, /activation_code/)
  assert.match(customerPortalSource, /confirm_password/)
  assert.ok(customerPortalSource.includes("客户服务账号"))
  assert.ok(customerPortalSource.includes("一次性激活码"))
  assert.ok(customerPortalSource.includes("登录客户服务端"))
  assert.ok(customerPortalSource.includes("首次激活 / 重置密码"))
})
