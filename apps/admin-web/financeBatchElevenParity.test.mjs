import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import {
  caseFeeRefundStatusLabel,
  refundExportRequestParams,
  refundListRequest,
  refundSelectedExportRequestParams,
} from "./src/financeRefundHelpers.mjs";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("legacy fee refund status semantics are preserved", () => {
  assert.equal(
    caseFeeRefundStatusLabel({ data: { refund_status: "R100" } }),
    "不再办理",
  );
  assert.equal(
    caseFeeRefundStatusLabel({ data: { refund_amount: 100, refunded_amount: 100 } }),
    "已退",
  );
  assert.equal(
    caseFeeRefundStatusLabel({ data: { refund_amount: 100, refunded_amount: 20 } }),
    "未退",
  );
  assert.equal(
    caseFeeRefundStatusLabel({ data: { refund_status: "R50", refund_amount: 0, refunded_amount: 0 } }),
    "未退",
  );
  assert.equal(
    caseFeeRefundStatusLabel({ status: "待审批", data: {} }),
    "未退",
  );
  assert.equal(
    caseFeeRefundStatusLabel({ data: { refund_amount: 0, refunded_amount: 0 } }),
    "未退",
  );
  assert.equal(
    caseFeeRefundStatusLabel({ data: { refund_amount: 100, refunded_amount: 99.99 } }),
    "未退",
  );
});

test("refund list and both export modes carry the selected legacy group", () => {
  assert.deepEqual(refundListRequest(2, 20, "待审批", "lawfirm"), {
    url: "/finance/refunds/query",
    params: { page: 2, page_size: 20, status: "待审批", group: "lawfirm", scope: "company" },
  });
  assert.deepEqual(refundExportRequestParams("待审批", "trad"), {
    status: "待审批",
    group: "trad",
    scope: "company",
  });
  assert.deepEqual(refundSelectedExportRequestParams([3, 3, 1], "", "trad"), {
    ids: "3,1",
    group: "trad",
    scope: "company",
  });
});

test("refund page exposes group filtering, clear, and exports with that filter", () => {
  assert.match(source, /const \[refundGroupFilter, setRefundGroupFilter\] = useState\(""\)/);
  assert.match(source, /refundListRequest\(page, pageSize, status, group\)/);
  assert.match(source, /refundExportRequestParams\(refundStatusFilter, refundGroupFilter\)/);
  assert.match(source, /refundSelectedExportRequestParams\(\s*selectedRefundRows,\s*refundStatusFilter,\s*refundGroupFilter/);
  assert.match(source, /setRefundGroupFilter\(""\)/);
});

test("fee query renders the legacy refund status label and invoice routes expose detail/files", () => {
  assert.match(source, /caseFeeRefundStatusLabel\(row\)/);
  const pendingStart = source.indexOf("const invoicePendingOperation");
  const pendingEnd = source.indexOf("const openInvoiceNumberChange", pendingStart);
  assert.ok(pendingStart >= 0 && pendingEnd > pendingStart);
  const pendingBlock = source.slice(pendingStart, pendingEnd);
  assert.match(pendingBlock, /openInvoiceDetail\(row\)/);
  assert.match(pendingBlock, /openRecordFiles\(row/);
  for (const name of ["invoiceMineOperation", "invoiceCompanyOperation"]) {
    const start = source.indexOf(`const ${name}`);
    const end = source.indexOf("\n  };", start);
    assert.match(source.slice(start, end), /openRecordFiles\(row/);
  }
});
