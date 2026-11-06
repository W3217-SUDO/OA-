import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (name) => readFileSync(new URL(`../src/feedback/${name}`, import.meta.url), "utf8");

test("待审核出现在状态筛选、处理中分组和标签颜色里", () => {
  const manager = read("FeedbackManager.tsx");
  assert.match(manager, /const statuses = \["待审核", /);
  assert.match(manager, /open: \["待审核", /);
  assert.match(manager, /待审核: "orange"/);
});

test("审核通过按钮按后端 available_actions 显示，样式沿用主操作", () => {
  const detail = read("FeedbackDetail.tsx");
  assert.match(detail, /primaryActions = new Set\(\["审核通过", /);
  assert.match(detail, /actions\.map\(\(action\)/);
  assert.match(detail, /等待\$\{feedback\.reviewer_display_name/);
  assert.match(detail, /reviewer_active === false/);
});

test("审核设置入口只在问题处理中心给管理员，选项同时显示姓名和账号", () => {
  assert.match(read("FeedbackManager.tsx"), /center && canDelete && <FeedbackReviewSettings \/>/);
  const settings = read("FeedbackReviewSettings.tsx");
  assert.match(settings, /\$\{user\.display_name\}（\$\{user\.username\}）/);
  assert.match(settings, /必须选择审核人/);
});
