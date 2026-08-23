import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("archive review restores the legacy single panel and real approve/reject actions", () => {
  assert.match(source, /title=\{reviewing\?\.row\.status === "亏损内审" \? "内部审核" : "归档审核"\}/);
  for (const heading of ["案号", "案件阶段", "归档号", "审核备注", "操作"]) {
    assert.match(source, new RegExp(`title: "${heading}"`));
  }
  assert.match(source, /onClick=\{\(\) => void reviewArchive\(true\)\}>同意<\/Button>/);
  assert.match(source, /onClick=\{\(\) => void reviewArchive\(false\)\}>拒绝<\/Button>/);
  assert.match(source, /api\.post\(`\/cases\/\$\{reviewing\.row\.id\}\/archive\/review`/);
  assert.match(source, /approved,/);
  assert.doesNotMatch(source, /label: "通过归档审核"/);
  assert.doesNotMatch(source, /label: "驳回归档审核"/);
});
