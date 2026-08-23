import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const start = source.indexOf('data-testid="case-legacy-summary"');
const end = source.indexOf('</table>', start);
const summary = source.slice(start, end);

test("case detail summary keeps the legacy rows and exposes the original-case relation", () => {
  assert.ok(start >= 0 && end > start);
  const labels = [...summary.matchAll(/<th>([^<]+)<\/th>/g)].map((match) => match[1]);
  assert.deepEqual(labels, [
    "我方案号", "起诉案由", "案件阶段", "原告",
    "案件名称", "开庭律师", "被告",
    "客户", "经办律师", "第三人",
    "合同号", "调查员", "律师助理", "公证书号",
    "线索号", "立案日期", "仓库位置",
    "原案件号", "复制/关联说明",
    "诉讼标的", "判决/调解金额", "分案日期", "案源人",
  ]);
  assert.equal((summary.match(/<tr>/g) || []).length, 7);
  assert.match(summary, /openRelatedOriginalCase/);
});

test("legacy summary maps imported case detail keys", () => {
  for (const key of ["case_register_date", "case_divisional_date", "notarial_no", "warehouse", "litigation_amount", "settlement_amount"]) {
    assert.match(summary, new RegExp(key));
  }
});
