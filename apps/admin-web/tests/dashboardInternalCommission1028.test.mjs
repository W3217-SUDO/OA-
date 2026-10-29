// BUG20261028004/005：工作台“待审内部提成费用”只看内部提成-待审核和内部提成(退费)-待审核。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { load } from "./caseRework0918.helpers.mjs";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");

test("入口打开合并队列，权限沿用两个审核页", async () => {
  const { dashboardWorkspace } = await load("../src/dashboardWorkspace.ts", {});
  const target = dashboardWorkspace("dashboard-queue-internal-commission-audit");
  assert.deepEqual([target.label, target.view, target.kind], ["待审内部提成费用", "finance-internal-commission-audit", "finance"]);
  const { isWorkspaceRouteGranted } = await load("../src/workspacePermissions.ts", {});
  const route = "dashboard-queue-internal-commission-audit";
  assert.equal(isWorkspaceRouteGranted(route, new Set(["finance-internal-audit"])), true);
  assert.equal(isWorkspaceRouteGranted(route, new Set(["finance-internal-refund-audit"])), true);
  assert.equal(isWorkspaceRouteGranted(route, new Set(["finance-internal-fee-audit"])), false);
});

test("列表走 commission_all，审批按退费/普通提成分别提交", async () => {
  const { internalFinanceQueryRequest } = await load("../src/finance/hooks/useInternalFinanceQuery.ts", {});
  const request = internalFinanceQueryRequest("finance-internal-commission-audit", {}, 1, 15);
  assert.equal(request.path, "/finance/internal-review-requests");
  assert.equal(request.params.kind, "commission_all");
  const actions = read("../src/finance/services/paymentsActions.tsx");
  assert.match(actions, /\["refund", feeReviewTargets\.filter\(\(item\) => item\.data\?\.is_refund\)\]/);
  assert.match(actions, /\["commission", feeReviewTargets\.filter\(\(item\) => !item\.data\?\.is_refund\)\]/);
  assert.match(read("../src/finance/config/routeMetadata.ts"), /"finance-internal-commission-audit": "待审内部提成费用"/);
});
