import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import {
  normalizeRefundResponse,
  refundAmountUpdateRequest,
  refundBatchStatusRequest,
  refundExportRequestParams,
  refundListRequest,
  refundListErrorMessage,
  refundLoadFailure,
  refundPageSizeOptions,
  refundRequestParams,
  refundSelectedExportRequestParams,
  refundStatusOptions,
} from "./src/financeRefundHelpers.mjs";

const pageSource = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("refund requests keep bounded page coordinates and legacy page sizes", () => {
  assert.deepEqual(refundRequestParams(3, 15), {
    page: 3,
    page_size: 15,
    scope: "company",
  });
  assert.deepEqual(refundRequestParams(1, 20, "待审批"), {
    page: 1,
    page_size: 20,
    status: "待审批",
    scope: "company",
  });
  assert.deepEqual(refundListRequest(2, 50, "已退款"), {
    url: "/finance/refunds/query",
    params: { page: 2, page_size: 50, status: "已退款", scope: "company" },
  });
  assert.deepEqual([...refundPageSizeOptions], [10, 15, 20, 50, 100, 200]);
  assert.deepEqual([...refundStatusOptions], ["全部", "草稿", "待审批", "退款办理中", "已退款", "已驳回"]);
});

test("refund response normalization preserves total and fallback coordinates", () => {
  assert.deepEqual(
    normalizeRefundResponse(
      { items: [{ id: 8 }], total: 22, page: 2, page_size: 15 },
      1,
      10,
    ),
    { items: [{ id: 8 }], total: 22, page: 2, pageSize: 15 },
  );
  assert.deepEqual(normalizeRefundResponse(undefined, 4, 20), {
    items: [],
    total: 0,
    page: 4,
    pageSize: 20,
  });
});

test("refund full export uses the server-scoped export contract", () => {
  assert.deepEqual(refundExportRequestParams("待审批"), {
    status: "待审批",
    scope: "company",
  });
  assert.deepEqual(refundSelectedExportRequestParams([9, 4], "待审批"), {
    ids: "9,4",
    status: "待审批",
    scope: "company",
  });
});

test("refund production never substitutes generic record export or browser-built CSV", () => {
  assert.doesNotMatch(pageSource, /api\.get\("\/records\/export"/);
  assert.match(pageSource, /"\/finance\/refunds\/export"/);
  assert.match(pageSource, /"\/finance\/refunds\/export-selected"/);
  assert.doesNotMatch(pageSource, /buildRefundExportCsv/);
  const start = pageSource.indexOf("const exportRefunds");
  const end = pageSource.indexOf("const selectedSettlementRows", start);
  assert.ok(start >= 0 && end > start, "refund export handler should be present");
  const refundExportBlock = pageSource.slice(start, end);
  assert.match(refundExportBlock, /诉讼费退款-\$\{selectedOnly \? "选中" : "全部"\}-\$\{dayjs\(\)\.format\("YYYY-MM-DD"\)\}\.xls/);
  assert.doesNotMatch(refundExportBlock, /\.csv/);
});

test("refund amount and batch progress use dedicated audited mutation contracts", () => {
  assert.deepEqual(refundAmountUpdateRequest(8, 125.5, "更正金额"), {
    url: "/finance/refunds/8/amount",
    method: "patch",
    body: { amount: 125.5, comment: "更正金额" },
  });
  assert.deepEqual(refundBatchStatusRequest([8, 3, 8], "待审批", "批量提交"), {
    url: "/finance/refunds/status",
    method: "post",
    body: { ids: [8, 3], status: "待审批", comment: "批量提交" },
  });
});

test("refund pagination failure preserves list coordinates and exposes API detail", () => {
  const state = { items: [{ id: 9 }], total: 12, page: 2, pageSize: 15 };
  const failure = refundLoadFailure(state, {
    response: { data: { detail: "退款查询权限不足" } },
  });
  assert.strictEqual(failure.state, state);
  assert.equal(failure.message, "退款查询权限不足");
  assert.equal(refundListErrorMessage(new Error("network")), "退款列表查询出错.");
  assert.match(pageSource, /refundLoadFailure\(/);
  assert.match(pageSource, /loadRefunds\(page, size, refundStatusFilter, true\)/);
});

test("refund production wiring keeps selection, pagination, exports, and source navigation", () => {
  assert.match(pageSource, /selectedRowKeys: selectedRefundRows/);
  assert.match(pageSource, /pageSizeOptions: refundPageSizeOptions/);
  assert.match(pageSource, /exportRefunds\(false\)/);
  assert.match(pageSource, /exportRefunds\(true\)/);
  assert.match(pageSource, /openCaseDetail\(r\.data\.case_no\)/);
  assert.match(pageSource, /openCustomerDetail\(value, r\.data\.customer_no\)/);
  assert.match(pageSource, /refundStatusOptions/);
  assert.match(pageSource, /openRefundDetail\(r\)/);
  assert.match(pageSource, /title: "实际到账"/);
  assert.match(pageSource, /title: "退款凭证号"/);
});

test("refund submit action targets refund endpoint and never invoice endpoint", () => {
  const start = pageSource.indexOf("const refundColumns");
  const end = pageSource.indexOf("const transactionColumns", start);
  assert.ok(start >= 0 && end > start, "refund columns should be present");
  const refundBlock = pageSource.slice(start, end);
  assert.match(refundBlock, /submitFlow\("refunds", r\)/);
  assert.doesNotMatch(refundBlock, /submitFlow\("invoices", r\)/);
});
