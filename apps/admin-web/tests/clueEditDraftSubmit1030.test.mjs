// BUG20261030015：我的调查线索-待审批线索修改时可上传附件（不限格式），按钮为暂存线索/提交审批/取消；
// BUG20261030014：线索审核两个页面不再有“修改”。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const read = (path) => fs.readFileSync(new URL(`../src/investigation/${path}`, import.meta.url), "utf8");
const page = read("InvestigationCenterPage.tsx");
const modal = read("EditRecordModal.tsx");

test("线索审核两页没有修改按钮", () => {
  assert.ok(page.includes('"clue-audit-pending": ["查询", "刷新", "审批"],'));
  assert.ok(page.includes('"clue-audit-customer": ["查询", "刷新", "审批"],'));
});

test("待审批线索修改：暂存线索、提交审批、取消排一排，附件不限格式", () => {
  assert.match(modal, /<Space>\s*<Button onClick=\{clueDraft\.onSaveDraft\}>暂存线索<\/Button>\s*<Button type="primary" onClick=\{clueDraft\.onSubmit\}>提交审批<\/Button>\s*<Button onClick=\{onCancel\}>取消<\/Button>\s*<\/Space>/);
  assert.match(modal, /<input multiple type="file" onChange=/);
  assert.ok(!/<input multiple type="file" accept=/.test(modal));
  assert.ok(page.includes('editTarget?.module === "clue" && editTarget.status === "待审批" && initialTab === "clue-my-pending"'));
  assert.ok(page.includes('...(clueMode === "draft" ? { status: "草稿" } : resubmit ? { status: "待审批" } : {}),'));
});
