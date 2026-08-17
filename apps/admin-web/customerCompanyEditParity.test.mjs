import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const page = fs.readFileSync("src/CustomerCenterPage.tsx", "utf8");
const editStart = page.indexOf('className="customer-edit-modal"');
const editEnd = page.indexOf('<Modal\n        open={Boolean(portalResult)}', editStart);
const edit = page.slice(editStart, editEnd);

test("company customer edit uses the complete new-customer sections and fields", () => {
  assert.match(edit, /className="customer-create-form"/);
  for (const section of ["基本信息", "法人信息", "开票信息", "控制信息"]) {
    assert.match(edit, new RegExp(`<h3>${section}</h3>`));
  }
  const fields = ["客户名称", "客户编码", "客户状态", "客户类型", "注册地址", "邮编", "客户简称", "电话", "传真", "法人姓名", "身份证号", "职务", "开票地址", "统一社会信用代码", "开户行", "帐号", "建档日期", "客户来源", "是否共享", "客户等级", "上海市资助信息", "客户管理人", "客户联系人账号"];
  let previous = -1;
  for (const field of fields) {
    const position = edit.indexOf(`label="${field}"`);
    assert.ok(position > previous, `${field} is missing or out of order`);
    previous = position;
  }
  assert.match(edit, /name="serial_no"[^>]*rules=\{\[\{ required: true \}\]\}/);
  assert.match(edit, /name="credit_code"[^>]*>\s*<Input disabled=\{Boolean\(editing\)\}/);
});

test("customer source edit keeps the real save synchronization path", () => {
  assert.match(page, /const data = synchronizeCustomerSource\(/);
  assert.match(page, /data: filterCustomerPatchData\(editableData\)/);
  assert.match(page, /customer_source: data\.customer_source \|\| ""/);
  assert.match(page, /source_person: data\.source_person \|\| ""/);
});

test("company and department customer views expose customer portal actions", () => {
  assert.match(page, /const customerPortalActions = \[/);
  assert.match(page, /initialView === "customer-dept"[\s\S]*customerPortalActions/);
  assert.match(page, /initialView === "customer-company"[\s\S]*customerPortalActions/);
});
