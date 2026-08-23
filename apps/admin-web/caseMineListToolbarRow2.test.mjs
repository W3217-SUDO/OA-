import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const css = fs.readFileSync(new URL("./src/case-center.css", import.meta.url), "utf8");

assert.match(source, /export const isMyCaseListRoute/);
for (const route of ["case-mine", "case-mine-civil", "case-mine-criminal", "case-mine-administrative", "case-mine-counsel", "case-mine-arbitration"]) {
  assert.ok(
    route === "case-mine"
      ? source.includes('initialView === "case-mine"')
      : source.includes('initialView.startsWith("case-mine-")'),
    `${route} must be covered by the shared 我的案件 route guard`,
  );
}

assert.match(source, /shouldShowCaseListActions\(initialView\)/);
assert.match(source, /aria-label="导出案件"/);
for (const label of ["导出选中（Excel）", "导出当前查询（Excel）", "导出选中归档清单（Excel）", "导出选中二维码（Word）"]) assert.match(source, new RegExp(label));
assert.match(source, />上传文件<\/Button>/);
assert.match(source, /selectedCaseKeys\.length !== 1 \|\| !selectedCaseCapability\.can_upload_attachment/);
assert.match(source, /aria-label="更多案件操作"/);
for (const label of [
  "上传案件文档", "新增律所费用", "新增平台费用", "新增内部费用", "批量修改",
  "修改开庭律师", "修改经办律师", "修改律师助理", "修改案件阶段",
  "生成授权委托书", "生成律所函", "生成身份证明", "生成结算提成表",
  "案件任务", "案件日志", "导出案件打印表",
]) {
  assert.match(source, new RegExp(label), `${label} must be available from the legacy selected-case operation menu`);
}
assert.match(source, /api\.post\(`\/cases\/\$\{row\.id\}\/documents\/\$\{documentType\}`\)/);
assert.match(source, /openCaseFee\(selectedCase, "律所", key\.slice/);
assert.match(source, /openCaseFee\(selectedCase, "平台", key\.slice/);
assert.match(source, /openCounselDetail\(selectedCase, "case-logs"\)/);
assert.match(source, /activeKey=\{activeCounselDetailTab\}/);
assert.match(css, /\.case-mine-list-actions \{ flex:0 0 auto/);

console.log("case mine list toolbar row 2 contract passed");
