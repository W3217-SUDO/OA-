// 501295：“问题反馈”固定在顶部“工作台”页签右边（陶国南 11-03 21:34），左侧菜单和左下角不再有；
// 管理员的“问题处理中心”在左侧菜单“工作台”下面。以后改回只改 FEEDBACK_MENU_PLACEMENT。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const feedback = fs.readFileSync(new URL("../src/BugFeedback.tsx", import.meta.url), "utf8");
const app = fs.readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");

test("问题反馈固定在工作台页签右边，别处不重复", () => {
  assert.match(feedback, /export const FEEDBACK_MENU_PLACEMENT: "tab" \| "top" \| "bottom" = "tab";/);
  assert.match(feedback, /\[\.\.\.rest\.slice\(0, at \+ 1\), entry, \.\.\.rest\.slice\(at \+ 1\)\]/);
  assert.match(feedback, /\{ key: FEEDBACK_ROUTE, label: "问题反馈", icon: <QuestionCircleOutlined \/> \},/);
  assert.match(feedback, /administrator \? \[\{ key: FEEDBACK_CENTER_ROUTE, label: "问题处理中心"/);
  assert.match(feedback, /if \(FEEDBACK_MENU_PLACEMENT !== "bottom"\) return null;/);
  assert.match(app, /items=\{withFeedbackTab\(visibleOpenPages\)\.map/);
  assert.match(app, /closable: item\.key !== "dashboard" && !isPinnedFeedbackTab\(item\.key\)/);
  assert.match(app, /const sidebarMenuItems = withFeedbackMenu\(sideMenuItems, permissionAdministrator\);/);
});
