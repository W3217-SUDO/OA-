// 501295：“问题反馈”固定在顶部“工作台”页签右边（陶国南 11-03 21:34）；
// 左侧的保留（21:41），位置按陶威 11-03 挪回侧栏最下面，手机端放在菜单末尾。改位置只改 BugFeedback.tsx 的两个常量。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const feedback = fs.readFileSync(new URL("../src/BugFeedback.tsx", import.meta.url), "utf8");
const app = fs.readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");

test("顶部页签保留，左侧回到最下面，手机端在菜单末尾", () => {
  assert.match(feedback, /export const FEEDBACK_TOP_TAB = true;/);
  assert.match(feedback, /export const FEEDBACK_SIDEBAR_POSITION: "bottom" \| "dashboard" = "bottom";/);
  assert.match(feedback, /if \(FEEDBACK_SIDEBAR_POSITION === "bottom" && !narrow\) return items;/);
  assert.match(feedback, /if \(FEEDBACK_SIDEBAR_POSITION === "bottom"\) return \[\.\.\.rest, \.\.\.entries\];/);
  assert.match(feedback, /if \(FEEDBACK_SIDEBAR_POSITION !== "bottom"\) return null;/);
  assert.match(app, /const sidebarMenuItems = withFeedbackMenu\(sideMenuItems, permissionAdministrator, isNarrowViewport\);/);
  assert.match(app, /\{!isNarrowViewport && <BugFeedback onOpen=\{\(\) => navigate\(FEEDBACK_ROUTE\)\}/);
  assert.match(app, /items=\{withFeedbackTab\(visibleOpenPages\)\.map/);
  assert.match(app, /closable: item\.key !== "dashboard" && !isPinnedFeedbackTab\(item\.key\)/);
});
