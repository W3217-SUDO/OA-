// 501295：“问题反馈”放到左侧菜单“工作台”下面紧挨着，左下角那个去掉；以后改回只改 FEEDBACK_MENU_PLACEMENT。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const feedback = fs.readFileSync(new URL("../src/BugFeedback.tsx", import.meta.url), "utf8");
const app = fs.readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");

test("问题反馈在工作台下面，底部不再重复", () => {
  assert.match(feedback, /export const FEEDBACK_MENU_PLACEMENT: "top" \| "bottom" = "top";/);
  assert.match(feedback, /findIndex\(\(item\) => item\.key === "dashboard"\)/);
  assert.match(feedback, /\[\.\.\.rest\.slice\(0, at \+ 1\), \.\.\.entries, \.\.\.rest\.slice\(at \+ 1\)\]/);
  assert.match(feedback, /if \(FEEDBACK_MENU_PLACEMENT === "top"\) return null;/);
  assert.match(feedback, /administrator \? \[\{ key: FEEDBACK_CENTER_ROUTE, label: "问题处理中心"/);
  assert.match(app, /const sidebarMenuItems = withFeedbackMenu\(sideMenuItems, permissionAdministrator\);/);
  assert.match(app, /menuItemsWithDoubleClickReload\(sidebarMenuItems,/);
  assert.match(app, /flattenMenu\(sidebarMenuItems\)\.find\(entry => entry\.key === key\);\n\s*if \(!item \|\| item\.disabled\) return;\n\s*setCollapsedOpenKeys/);
});
