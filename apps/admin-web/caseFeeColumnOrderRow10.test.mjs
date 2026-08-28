import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const page = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("row 10 follows the exact legacy external fee column order", () => {
  const columns = page.match(/const externalCaseFeeColumns=\[([\s\S]*?)\n  \];/)?.[1] || "";
  const titles = [...columns.matchAll(/title:\"([^\"]+)\"/g)].map((match) => match[1]);
  assert.deepEqual(titles, [
    "合同编号", "费用类型", "金额", "退费", "提交人", "提交日期",
    "回款日期", "回款金额", "开票日期", "发票号", "申请付款金额",
  ]);
  assert.doesNotMatch(columns, /title:\"付款账号\"/);
});

test("row 10 makes non-zero received amounts open the fee detail", () => {
  const columns = page.match(/const externalCaseFeeColumns=\[([\s\S]*?)\n  \];/)?.[1] || "";
  assert.match(columns, /title:\"回款金额\"[\s\S]*?Number\(value\|\|0\)!==0/);
  assert.match(columns, /<Button type=\"link\" className=\"case-cell-link\" onClick=\{\(\)=>void openRelatedFee\(row\)\}>\{value\}<\/Button>/);
});
