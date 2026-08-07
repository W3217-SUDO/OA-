import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/InvestigationCenterPage.tsx", import.meta.url), "utf8");
const clueColumns = source.slice(source.indexOf('if (initialTab.startsWith("clue-"))'));

test("company investigation clues retain the legacy list column order", () => {
  const labels = [
    "线索编号", "案件编号", "调查员", "调查时间", "取证时间", "侵权方式",
    "店铺名称", "店铺Id", "调查地址", "权利人", "权利类型", "案源人",
    "客户管理人", "公证书号", "仓库", "费用金额",
  ];
  let previous = -1;
  for (const label of labels) {
    const current = clueColumns.indexOf(`title: \"${label}\"`);
    assert.ok(current > previous, `${label} should follow the legacy column order`);
    previous = current;
  }
  assert.equal(clueColumns.includes('title: "来源调查任务"'), false);
});
