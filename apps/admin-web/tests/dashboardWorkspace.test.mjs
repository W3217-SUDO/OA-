import test from "node:test";
import assert from "node:assert/strict";
import { load } from "./caseRework0918.helpers.mjs";

const proxy = values => new Proxy(values, { get: (target, key) => key in target ? target[key] : () => {} });

test("八个控制台入口均解析为完整业务页，非法入口不放行", async () => {
  const { dashboardWorkspace, dashboardWorkspaces } = await load("../src/dashboardWorkspace.ts", {});
  assert.equal(Object.keys(dashboardWorkspaces).length, 8);
  for (const [key, item] of Object.entries(dashboardWorkspaces)) {
    const result = dashboardWorkspace("dashboard-queue-" + key);
    assert.equal(result.view, item.view);
    assert.ok(["finance", "case", "receivable"].includes(result.kind));
  }
  assert.equal(dashboardWorkspace("dashboard-queue-invalid"), null);
  assert.equal(dashboardWorkspace("dashboard-queue-__proto__"), null);
});

test("控制台费用查询只加载当前业务和人员，不依赖其他财务列表", async () => {
  for (const [queue, path] of [["official-fee-unpaid", "/finance/fees/query"], ["refund-pending", "/finance/case-fees/refunds"]]) {
    const requests = [], messages = [], rows = [];
    const { createFinanceQueriesActions } = await load("../src/finance/services/queriesActions.tsx", {
      get: async (url, options) => { requests.push([url, options]); return { data: { items: [{ id: 9 }], total: 1, page: 1, page_size: 15, username: "person" } }; },
    }, messages);
    const actions = createFinanceQueriesActions(proxy({
      dashboardQueue: queue, initialView: queue === "refund-pending" ? "finance-refund" : "finance-fee-query",
      isRefundCaseFeeRoute: queue === "refund-pending", feeQueryParams: () => ({ dashboard_queue: queue }),
      setFeeQueryRows: value => rows.push(value),
    }));
    await actions.load();
    assert.deepEqual(requests.map(([url]) => url), [path, "/auth/me", "/people/options"]);
    assert.equal(requests[0][1].params.dashboard_queue, queue);
    assert.deepEqual(rows, [[{ id: 9 }]]);
    assert.deepEqual(messages, []);
  }
});

test("案件查询、分页及清空都携带固定控制台队列", async () => {
  const requests = [], messages = [];
  const { createCaseQueriesActions } = await load("../src/legal/services/queriesActions.tsx", {
    post: async (path, body) => { requests.push(body); return { data: { items: [], total: 0, page: body.page, page_size: body.page_size, phase_counts: {} } }; },
  }, messages);
  const actions = createCaseQueriesActions(proxy({
    dashboardQueue: "appeal-pending", caseQuery: {}, originalPageSize: 15, ordinaryCaseQueue: "", ordinaryScope: "company", ordinaryCaseTypes: [],
    ordinaryRequestGuard: { begin: () => 1, isLatest: () => true },
  }));
  await actions.loadOrdinaryCases({ keyword: "关键词" }, 2, 15);
  await actions.loadOrdinaryCases({}, 1, 15);
  assert.equal(requests[0].keyword, "关键词");
  assert.equal(requests[0].page, 2);
  assert.equal(requests[1].keyword, "");
  for (const body of requests) assert.equal(body.dashboard_queue, "appeal-pending");
  assert.deepEqual(messages, []);
});
