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
assert.match(source, /导出选中（Excel）/);
assert.match(source, /导出当前查询（Excel）/);
assert.match(source, /上传案件文件/);
assert.match(source, /selectedCaseKeys\.length !== 1 \|\| !selectedCaseCapability\.can_upload_attachment/);
assert.match(source, /aria-label="更多案件操作"/);
assert.match(source, /key: "participant"/);
assert.match(source, /key: "fee"/);
assert.match(source, /key: "assign"/);
assert.match(source, /key: "archive"/);
assert.match(css, /\.case-mine-list-actions \{ flex:0 0 auto/);

console.log("case mine list toolbar row 2 contract passed");
