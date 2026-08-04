import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/LawFirmPage.tsx", import.meta.url), "utf8");

test("law firm list restores legacy columns", () => {
  assert.match(source, /title:"邮编"[\s\S]*dataIndex:"postal_code"/);
  assert.match(source, /title:"传真"[\s\S]*dataIndex:"fax"/);
  assert.match(source, /title:"国家地区"[\s\S]*dataIndex:"country"/);
  assert.match(source, /title:"机构代码"[\s\S]*dataIndex:"organization_code"/);
  assert.match(source, /title:"公司代码"[\s\S]*dataIndex:"company_code"/);
  assert.match(source, /title:"营业地址"[\s\S]*dataIndex:"business_address"/);
});

test("law firm contact table restores legacy columns and direct status actions", () => {
  assert.match(source, /dataSource=\{contacts\}[\s\S]*title:"序号"[\s\S]*dataIndex:"id"/);
  assert.match(
    source,
    /title:"邮编"[\s\S]*dataIndex:"postal_code"[\s\S]*title:"传真"[\s\S]*dataIndex:"fax"[\s\S]*title:"创建人"[\s\S]*dataIndex:"created_by"[\s\S]*title:"创建时间"[\s\S]*dataIndex:"created_at"/,
  );
  assert.match(source, /toggleContactActive\(row\)/);
  assert.match(source, /联系人已停用/);
  assert.match(source, /联系人已启用/);
});

test("law firm contact modal restores legacy required fields", () => {
  assert.match(source, /name="address" label="联系地址" rules=\{\[\{required:true,message:'请输入联系地址'\}\]\}/);
  assert.match(source, /name="postal_code" label="邮编" rules=\{\[\{required:true,message:'请输入邮编'\}\]\}/);
  assert.match(source, /name="phone" label="联系电话" rules=\{\[\{required:true,message:'请输入联系电话'\}\]\}/);
  assert.match(source, /name="fax" label="传真" rules=\{\[\{required:true,message:'请输入传真'\}\]\}/);
  assert.match(source, /name="email" label="邮箱" rules=\{\[\{required:true,message:'请输入邮箱'\}\]\}/);
});

test("law firm list keeps a direct contact-management entry", () => {
  assert.match(source, /openContacts\(row\)/);
  assert.match(source, />联系人<\/Button>/);
});