// 501149 全站排查：列表、表格里的法院显示全称；对不上的显示原值。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { caseCourtName } from "../src/legal/courtDisplay.ts";

const resolved = (name, raw) => ({ status: "resolved", raw, name, error: "" });

test("有全称用全称，否则显示原值", () => {
  assert.equal(caseCourtName({ court: "冀01", court_displays: { court: resolved("河北省石家庄市中级人民法院", "冀01") } }), "河北省石家庄市中级人民法院");
  assert.equal(caseCourtName({ court: "X99", court_displays: { court: { status: "unresolved", raw: "X99", name: "", error: "x" } } }), "X99");
  assert.equal(caseCourtName({ court: "黄浦法院" }), "黄浦法院");
  assert.equal(caseCourtName({ execution_instance_court: "沪01" }, "execution"), "沪01");
  assert.equal(caseCourtName(undefined), "");
});

test("刑事案件、案件列表、归档、关联案件、客户端都改用全称", () => {
  for (const file of ["src/legal/CaseCenterPage.tsx", "src/legal/columns/caseColumns.tsx", "src/legal/columns/originalArchiveColumns.tsx",
    "src/legal/columns/specialColumns.tsx", "src/investigation/LinkedCaseModal.tsx", "src/CustomerPortalPage.tsx"]) {
    const source = fs.readFileSync(new URL(`../${file}`, import.meta.url), "utf8");
    assert.match(source, /caseCourtName\(/, file);
    assert.doesNotMatch(source, /row\.data\.court\s*\|\|\s*row\.data\.first_court_name|r\.data\.court \|\| "-"|row\.data\.court \|\| "" \}/, file);
  }
});
