import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const app = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
const page = readFileSync(new URL("../src/investigation/InvestigationCenterPage.tsx", import.meta.url), "utf8");

test("501692 菜单改名“公证书号仓库信息导入”放第一位，不再出现“取证信息文件导入”", () => {
  const menus = app.match(/key: "notary-import-storage", label: "([^"]+)" \},\n\s*\{ key: "notary-import-info"/g) || [];
  assert.equal(menus.length, 2);
  assert.ok(menus.every((item) => item.includes("公证书号仓库信息导入")));
  assert.match(app, /"notary-import-storage": "公证书号仓库信息导入"/);
  assert.doesNotMatch(app, /label: "取证信息文件导入"/);
});

test("501692 公证书号仓库信息导入收 Excel 和 CSV", () => {
  assert.match(page, /initialTab === "notary-import-storage"\n\s*\? "\.xlsx,\.xls,\.csv/);
  assert.match(page, /支持 Excel（\.xlsx \/ \.xls）或 UTF-8 CSV/);
});
