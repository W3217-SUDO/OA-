import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/InvestigationCenterPage.tsx", import.meta.url), "utf8");

test("clue detail restores legacy file and evidence workbench", () => {
  for (const text of ["线索文件", "取证信息", "取证机构", "公证书号", "取证时间", "证物存放处", "证物状态"]) {
    assert.ok(source.includes(text), `missing ${text}`);
  }
  assert.match(source, /rowSelection=\{\{ type: "radio"/);
  assert.match(source, /\/investigations\/clues\/\$\{investigationDetail\.id\}\/workspace/);
  assert.match(source, /api\.put\(`\/investigations\/evidence\/\$\{editingEvidence\.id\}`/);
  assert.match(source, /api\.delete\(`\/investigations\/evidence\/\$\{selectedEvidence\.id\}`/);
});
