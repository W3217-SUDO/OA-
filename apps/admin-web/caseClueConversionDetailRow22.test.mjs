import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("row 22 displays the converted cause and source clue in case detail", () => {
  assert.match(source, /data\.cause_or_charge\|\|viewingCounselCase\.data\.cause_of_action/);
  assert.match(source, /setCounselDetailClues\(relationRes\.status === "fulfilled" \? relationRes\.value\.data\.clues \|\| \[\] : \[\]\)/);
});

test("row 22 restores legacy clue information columns", () => {
  for (const label of ["线索号", "调查时间", "店铺名称", "店铺地址", "公证书号", "公证书状态", "公证书入库时间", "件数", "仓库名称", "仓库位置", "证物状态"]) {
    assert.match(source, new RegExp(`title:\"${label}\"`));
  }
});
