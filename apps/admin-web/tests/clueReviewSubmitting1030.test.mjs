// BUG20261030016：线索审批“同意/拒绝”提交中显示加载并锁住，防止连点重复审批。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const modal = fs.readFileSync(new URL("../src/investigation/ClueReviewModal.tsx", import.meta.url), "utf8");

test("同意/拒绝提交中锁住按钮并显示提交中", () => {
  assert.ok(modal.includes("if (submittingRef.current) return;"));
  assert.ok(modal.includes('onClick={() => submit(true)}>{submitting === true ? "提交中" : "同意"}</Button>'));
  assert.ok(modal.includes('onClick={() => submit(false)}>{submitting === false ? "提交中" : "拒绝"}</Button>'));
  assert.ok(modal.includes("disabled={submitting === false ||"));
  assert.ok(modal.includes("disabled={submitting === true ||"));
  assert.ok(modal.includes("confirmLoading={submitting !== null}"));
});
