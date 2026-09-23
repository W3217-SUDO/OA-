import test from "node:test";
import assert from "node:assert/strict";
import { resolveNotificationNavigation } from "../src/notificationNavigation.ts";

test("个人任务通知可进入个人列表，不授予公司任务菜单", () => {
  for (const route of ["task-my-accepted", "task-my-created", "task-my-collaborating"]) {
    const result = resolveNotificationNavigation(
      { source_type: "task", source_id: 8, target_route: route }, new Set(),
    );
    assert.equal(result.route, route);
    assert.equal(result.allowed, true);
  }
  assert.equal(resolveNotificationNavigation(
    { source_type: "task", source_id: 8, target_route: "task-company-accepted" }, new Set(),
  ).allowed, false);
});

test("仅有公司案件菜单也能进入关联案件详情，其他模块仍按菜单校验", () => {
  const caseResult = resolveNotificationNavigation(
    { source_type: "case", source_id: 17, source_serial_no: "SHMS2600017", target_route: "case-mine" },
    new Set(["case-company"]),
  );
  assert.equal(caseResult.route, "case-detail-17-SHMS2600017");
  assert.equal(caseResult.allowed, true);
  assert.equal(resolveNotificationNavigation(
    { source_type: "finance", source_id: 9, target_route: "finance-audit" },
    new Set(["case-company"]),
  ).allowed, false);
});
