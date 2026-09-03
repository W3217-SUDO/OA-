import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const finance = readFileSync(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");
const app = readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("9.2 row 4 routes dashboard refunds to the full refund query workbench", () => {
  assert.match(app, /"finance-refund": "退费查询"/);
  assert.match(finance, /"finance-refund": \{[\s\S]*?"案件编号"[\s\S]*?"法院案号"[\s\S]*?"法院名称"[\s\S]*?"付款时间"[\s\S]*?"退费进度"[\s\S]*?"退费金额"/);
  assert.match(finance, /\/finance\/case-fees\/refunds/);
  for (const header of ["原告", "被告", "案件阶段", "律师助理", "开庭律师", "费用类型", "退费金额", "新建时间", "进度时长"]) {
    assert.match(finance, new RegExp(`"${header}"`));
  }
});

test("9.2 row 4 wires exports, legacy more-actions, refund actions and not-required marking", () => {
  assert.match(finance, /\/finance\/case-fees\/refunds\/export/);
  for (const label of ["导出选中", "导出全部", "更多操作", "新增官费", "新增代理费", "新增其他费用", "退费进度修改", "添加法院日志", "添加到账日志", "添加其他日志", "标记不再办理退费"]) {
    assert.match(finance, new RegExp(label));
  }
  assert.match(finance, /\/finance\/case-fees\/refunds\/status/);
  assert.match(finance, /\/finance\/case-fees\/refunds\/logs/);
});
