import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const modalStart = source.indexOf('<Drawer open={Boolean(caseTaskCreateCase)}');
const modalEnd = source.indexOf('</Drawer>', modalStart) + '</Drawer>'.length;
const taskModal = source.slice(modalStart, modalEnd);

test("row 19 searches task owners by Chinese display label", () => {
  assert.match(taskModal, /label="负责人"[\s\S]*?<Select showSearch optionFilterProp="label" options=\{caseAssistantOptions\}/);
  assert.match(taskModal, /placeholder="输入中文姓名检索"/);
  assert.doesNotMatch(taskModal, /label="负责人"[\s\S]*?<Input \/>/);
});

test("row 19 searches collaborators from the same employee options", () => {
  assert.match(taskModal, /label="协作人"[\s\S]*?<Select mode="multiple" showSearch optionFilterProp="label" options=\{caseAssistantOptions\}/);
  assert.doesNotMatch(taskModal, /mode="tags"|输入账号后回车/);
});
