import test from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const compiled = await build({
  entryPoints: [fileURLToPath(new URL("../src/notificationNavigation.ts", import.meta.url))],
  bundle: true, write: false, platform: "node", format: "esm", logLevel: "silent",
});
const { resolveNotificationNavigation } = await import(`data:text/javascript;base64,${Buffer.from(compiled.outputFiles[0].text).toString("base64")}`);

test("个人任务通知需明确页面授权，不授予公司任务菜单", () => {
  for (const route of ["task-my-accepted", "task-my-created", "task-my-collaborating"]) {
    const result = resolveNotificationNavigation(
      { source_type: "task", source_id: 8, target_route: route }, new Set([route]),
    );
    assert.equal(result.route, route);
    assert.equal(result.allowed, true);
    const denied = resolveNotificationNavigation(
      { source_type: "task", source_id: 8, target_route: route }, new Set(),
    );
    assert.equal(denied.route, route);
    assert.equal(denied.allowed, false);
    for (const otherRoute of ["task-my-accepted", "task-my-created", "task-my-collaborating"].filter((key) => key !== route)) {
      assert.equal(resolveNotificationNavigation(
        { source_type: "task", source_id: 8, target_route: route }, new Set([otherRoute]),
      ).allowed, false);
    }
    assert.equal(resolveNotificationNavigation(
      { source_type: "task", source_id: 8, target_route: "task-company-accepted" }, new Set([route]),
    ).allowed, false);
  }
  assert.equal(resolveNotificationNavigation(
    { source_type: "task", source_id: 8, target_route: "task-company-accepted" }, new Set(),
  ).allowed, false);
  assert.equal(resolveNotificationNavigation(
    { source_type: "task", source_id: 8, target_route: "task-company-accepted" }, new Set(["task-company-accepted"]),
  ).allowed, true);
});

test("仅有公司案件菜单也能进入关联案件详情，其他模块仍按菜单校验", () => {
  const caseResult = resolveNotificationNavigation(
    { source_type: "case", source_id: 17, source_serial_no: "SHMS2600017", target_route: "case-mine" },
    new Set(["case-company"]),
  );
  assert.equal(caseResult.route, "case-detail-17-SHMS2600017");
  assert.equal(caseResult.allowed, true);
  assert.equal(resolveNotificationNavigation(
    { source_type: "case", source_id: 17, source_serial_no: "SHMS2600017", target_route: "case-mine" },
    new Set(),
  ).allowed, false);
  assert.equal(resolveNotificationNavigation(
    { source_type: "case", source_id: 17, source_serial_no: "SHMS2600017", target_route: "case-mine" },
    new Set(["case-mine-civil"]),
  ).allowed, true);
  assert.equal(resolveNotificationNavigation(
    { source_type: "case", source_id: 17, source_serial_no: "SHMS2600017", target_route: "case-mine" },
    new Set(["task-my-accepted"]),
  ).allowed, false);
  assert.equal(resolveNotificationNavigation(
    { source_type: "finance", source_id: 9, target_route: "finance-audit" },
    new Set(["case-company"]),
  ).allowed, false);
  assert.equal(resolveNotificationNavigation(
    { source_type: "finance", source_id: 9, target_route: "finance-audit" },
    new Set(["finance-audit"]),
  ).allowed, true);
});
