import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const page = fs.readFileSync("src/CustomerCenterPage.tsx", "utf8");
const api = fs.readFileSync("../api-server/app/main.py", "utf8");

test("customer portal opening uses bound contact accounts and supports multiple-account selection", () => {
  const open = api.slice(api.indexOf("async def open_customer_portal"), api.indexOf("\n\n@app", api.indexOf("async def open_customer_portal")));
  assert.match(open, /contact_accounts/);
  assert.match(open, /请先在客户编辑中绑定客户联系人账号/);
  assert.match(open, /绑定了多个联系人账号，请选择/);
  assert.match(open, /服务账号必须从该客户已绑定的联系人账号中选择/);
  assert.match(open, /User\.is_active\.is_\(True\)/);
  assert.doesNotMatch(open, /f"vip-\{customer\.serial_no\}"/);
});

test("customer management offers an account picker and explains portal login delivery", () => {
  assert.match(page, /setPortalCustomer/);
  assert.match(page, /accounts\.length > 1/);
  assert.match(page, /选择客户服务账号/);
  assert.match(page, /登录入口：客户服务端/);
  assert.match(page, /window\.location\.origin.*customer-portal/);
  assert.match(page, /Array\.isArray\(customer\.data\.contact\)/);
  assert.match(page, /openPortal\(target, accounts\[0\]/);
});
