// 501150：待退费原告/被告合成一栏（上原告下被告）；操作列收窄靠右，进度时长放宽。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const routes = fs.readFileSync(new URL("../../src/finance/config/routeConfigs.tsx", import.meta.url), "utf8");
const columns = fs.readFileSync(new URL("../../src/finance/columns/configuredColumns.tsx", import.meta.url), "utf8");

test("待退费表头原告/被告合一栏", () => {
  const refund = routes.slice(routes.indexOf('"finance-refund": {'));
  const headers = refund.slice(refund.indexOf("headers: ["), refund.indexOf("],", refund.indexOf("headers: [")));
  assert.match(headers, /"案号",\s*"原告\/被告",\s*"案件阶段",\s*"开庭律师\/律师助理",\s*"费用类型"/);
  assert.doesNotMatch(headers, /"原告",|"被告",|"律师助理",|"开庭律师",|"退费进度",|"进度时长",/);
  assert.match(headers, /"法院名称",\s*"进度及时长",\s*"操作"/);
});

test("合一栏上原告下被告，操作列靠右收窄、进度时长放宽", () => {
  assert.match(columns, /header === "原告\/被告" \? \(<div className="finance-party-stack">\s*<span><i>原告<\/i>[^\n]*\n\s*<span><i>被告<\/i>/);
  assert.match(columns, /header === "开庭律师\/律师助理" \? \(<div className="finance-party-stack">\s*<span><i>律师<\/i>\{context\.cellValue\(row, "开庭律师"\)[^\n]*\n\s*<span><i>助理<\/i>\{context\.cellValue\(row, "律师助理"\)/);
  const widths = columns.slice(columns.indexOf("const refundColumnWidths"), columns.indexOf("};", columns.indexOf("const refundColumnWidths")));
  const width = (name) => Number(new RegExp(`${name}: (\\d+)`).exec(widths)[1]);
  assert.ok(width("操作") < 100);
  assert.ok(width("进度及时长") >= 140 && width("进度及时长") <= 160);
  assert.ok(width("费用类型") <= 90);
  assert.match(widths, /"开庭律师\/律师助理": 110,/);
  assert.match(columns, /header === "进度及时长" \? \(<div className="finance-party-stack finance-stack-nowrap">\s*<span><i>进度<\/i>\{context\.cellValue\(row, "退费进度"\)[^\n]*\n\s*<span><i>时长<\/i>\{row\.data\?\.refund_progress_days == null \? "—" : `\$\{row\.data\.refund_progress_days\} 天`\}/);
  const view = fs.readFileSync(new URL("../../src/finance/FinanceOriginalRoutesView.tsx", import.meta.url), "utf8");
  assert.match(view, /x: isFeeQueryRoute \|\| isRefundCaseFeeRoute\s*\? originalColumns\.reduce/);
  assert.match(columns, /context\.isRefundCaseFeeRoute && header === "操作" \? \("right" as const\)/);
  assert.match(columns, /context\.isRefundCaseFeeRoute && header === "操作" \? \{ align: "right" as const \}/);
});

test("进度及时长自适应时不压窄，从别的列匀宽度（陶国南 11-03）", () => {
  assert.match(columns, /header === "进度及时长" \? \{ className: "oa-fit-nowrap", sorter:/);
  const table = fs.readFileSync(new URL("../../src/components/ResizableTable.tsx", import.meta.url), "utf8");
  assert.match(table, /const keepLine = typeof column\.className === "string" && column\.className\.split\(\/\\s\+\/\)\.includes\("oa-fit-nowrap"\)/);
  assert.match(table, /keepLine \? Math\.ceil\(wide\) \+ 8 :/);
  assert.match(table, /const finalMin = unbreakable \|\| totalMin \|\| keepLine \? min :/);
});
