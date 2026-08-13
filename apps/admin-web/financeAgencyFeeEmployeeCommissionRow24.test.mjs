import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");
const caseSource = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("agency fee form supports creating multiple employee commissions", () => {
  assert.match(source, /selectedFeeType === "代理费"/);
  assert.match(source, /<Form\.List name="commission_details">/);
  assert.match(source, /新建员工提成/);
  assert.match(source, /name=\{\[field\.name, "employee_username"\]\}/);
  assert.match(source, /options=\{financePeople\.map/);
  assert.match(source, /已分配员工提成/);
});

test("editing an agency fee restores its employee commission details", () => {
  assert.match(source, /commission_details: Array\.isArray\(data\.commission_details\)/);
  assert.match(source, /employee_username: detail\.employee_username/);
});

test("case fee entry renders employee commissions for agency fees", () => {
  assert.match(caseSource, /feeExpenseSubtype === "代理费"/);
  assert.match(caseSource, /<Form\.List name="commission_details">/);
  assert.match(caseSource, /新建员工提成/);
  assert.match(caseSource, /name=\{\[field\.name, "employee_username"\]\}/);
  assert.match(caseSource, /feeEmployeeOptions/);
});
