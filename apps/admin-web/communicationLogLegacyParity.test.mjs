import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const page = fs.readFileSync(new URL("./src/CommunicationLogPage.tsx", import.meta.url), "utf8");
const style = fs.readFileSync(new URL("./src/communication-log.css", import.meta.url), "utf8");

test("communication log uses server-side pagination", () => {
  assert.match(page, /keyword:customerName[\s\S]*mine_only:isAdmin\?mineOnly:true[\s\S]*page:nextPage,page_size:nextPageSize/);
  assert.match(page, /setTotal\(data\.total\|\|0\)/);
  assert.match(page, /pagination=\{\{current:page,pageSize,total/);
  assert.match(page, /onChange:\(nextPage,nextSize\)=>/);
});

test("communication create restores legacy required contact and phone", () => {
  assert.match(page, /name="contact" label="联系人" rules=\{!editing\?\[\{required:true,message:'请输入联系人'\}\]:undefined\}/);
  assert.match(page, /name="phone" label="联系电话" rules=\{!editing\?\[\{required:true,message:'请输入联系电话'\}\]:undefined\}/);
});

test("communication edit locks the customer and autofills the primary contact", () => {
  assert.match(page, /name="customer_record_id"[\s\S]*disabled=\{Boolean\(editing\)\}/);
  assert.match(page, /const applyCustomerDefaults=\(customerRecordId:number\)=>/);
  assert.match(page, /customer\?\.data\?\.contacts/);
  assert.match(page, /is_primary/);
  assert.match(page, /form\.setFieldsValue\(\{contact:primary\?\.name\|\|'',phone:primary\?\.office_phone\|\|primary\?\.phone\|\|''\}\)/);
});

test("communication view modal loads attachments and grouped history", () => {
  assert.match(page, /const \[viewAttachments,setViewAttachments\]=useState<Attachment\[\]>\(\[\]\)/);
  assert.match(page, /const loadViewAttachments=async\(communicationId:number\)=>/);
  assert.match(page, /const startView=\(row:Communication\)=>\{setViewing\(row\);setViewAttachments\(\[\]\);void loadViewAttachments\(row\.id\)\}/);
  assert.match(page, /dataSource=\{viewAttachments\}[\s\S]*renderItem=\{attachment=>/);
  assert.match(page, /groupCommunicationHistory\(/);
  assert.match(page, /communication-history-group/);
  assert.match(style, /\.communication-history-group/);
});

test("communication empty state keeps the legacy guidance copy", () => {
  assert.ok(page.includes("没有查询到符合条件的记录，可以去新增沟通记录。"));
});

test("communication content column keeps the legacy width", () => {
  assert.match(page, /title:'内容'[\s\S]*width:400/);
});