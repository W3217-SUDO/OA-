import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const casePage = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const financePage = fs.readFileSync(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");

test("case personnel rendering never falls back to the raw account", () => {
  assert.match(casePage, /return option\?\.label\.replace[\s\S]*?\|\| "姓名待维护"/);
  assert.doesNotMatch(casePage, /\?\.label \|\| normalized/);
  assert.match(casePage, /发票申请人",render:[\s\S]*?casePersonDisplayName\(row\.uploader,row\.uploader_display_name\)/);
  assert.match(casePage, /创建人",width:110,render:[\s\S]*?casePersonDisplayName\(row\.owner\)/);
  assert.match(casePage, /archive_submitter_display_name\|\|row\.owner_display_name/);
});

test("finance personnel rendering resolves system display names and uses a placeholder", () => {
  assert.match(financePage, /api\.get\("\/people\/options"\)/);
  assert.match(financePage, /return financePersonNameMap\.get\(key\) \|\| "姓名待维护"/);
  assert.match(financePage, /申请人: financePersonDisplayName/);
  assert.match(financePage, /客户管理人: financePersonDisplayName/);
  assert.match(financePage, /案源人: financePersonDisplayName/);
  assert.match(financePage, /调查员: financePersonDisplayName/);
  assert.match(financePage, /经办律师: financePersonDisplayNames/);
  assert.match(financePage, /审核人: financePersonDisplayName/);
});
