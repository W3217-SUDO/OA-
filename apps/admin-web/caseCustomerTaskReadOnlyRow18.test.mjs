import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const customerTabStart = source.indexOf('{key:"customer-tasks",label:"客户任务"');
const customerTabEnd = source.indexOf('{key:"clues",label:"线索信息"', customerTabStart);
const customerTab = source.slice(customerTabStart, customerTabEnd);

test("row 18 keeps the customer task tab read only", () => {
  assert.ok(customerTabStart >= 0 && customerTabEnd > customerTabStart);
  assert.match(customerTab, /dataSource=\{counselDetailCustomerTasks\}/);
  assert.doesNotMatch(customerTab, /发布客户任务|openCustomerTaskCreator|PlusOutlined/);
});

test("row 18 keeps case task publishing separate", () => {
  assert.match(source, /openCaseTaskCreator\(viewingCounselCase\)/);
  assert.doesNotMatch(source, /const openCustomerTaskCreator/);
});
