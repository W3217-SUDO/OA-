import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import {
  buildInvoiceApplicationPayload,
} from "./src/financeInvoiceHelpers.mjs";
import { internalFeeExportRequestParams } from "./src/financeInternalFeeHelpers.mjs";
import { refundStatusForRoute } from "./src/financeRefundHelpers.mjs";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const caseRecord = {
  id: 41,
  serial_no: "CASE-41",
  customer: "客户甲",
  title: "案件甲",
};
const contractRecord = {
  id: 77,
  serial_no: "CON-77",
  title: "合同甲",
  customer: "客户甲",
};
const caseFee = { id: 901, serial_no: "FEE-901", data: { case_no: "CASE-41" } };

test("F14-01 not-required refund route fixes R100 and clear query", () => {
  assert.equal(refundStatusForRoute("finance-refund-not-required", "全部"), "R100");
  assert.equal(refundStatusForRoute("finance-refund-not-required", "已退款"), "R100");
  assert.equal(refundStatusForRoute("finance-refund", "已退款"), "已退款");
  assert.match(source, /finance-refund-not-required/);
  assert.match(source, /R100/);
});

test("F14-01 route keeps fixed status when clearing filters", () => {
  assert.match(source, /refundStatusForRoute\(initialView, ""\)/);
  assert.match(source, /setRefundGroupFilter\(""\)/);
});

test("F14-05 fee mutation refresh is scoped instead of global load", () => {
  assert.match(source, /refreshCurrentFinanceFeeList/);
  const cancelBlock = source.match(/const submitPaymentCancel = async[\s\S]*?const openPaymentRollback/)[0];
  const rollbackBlock = source.match(/const submitPaymentRollback = async[\s\S]*?const voidRejectedInternalFee/)[0];
  assert.doesNotMatch(cancelBlock, /await load\(\)/);
  assert.doesNotMatch(rollbackBlock, /await load\(\)/);
});

test("F14-05 scoped refresh preserves page, status and query", () => {
  assert.match(source, /refreshCurrentFinanceFeeList\(\{[\s\S]*page[\s\S]*status[\s\S]*query/);
  assert.match(source, /createLatestRequestGuard/);
});

test("F14-12 invoice payload carries real case, contract and case-fee ids", () => {
  const result = buildInvoiceApplicationPayload({
    values: {
      customer: "客户甲",
      case_no: "CASE-41",
      contract_record_id: 77,
      case_fee_ids: [901, 901],
      amount: 123.45,
      invoice_title: "客户甲",
    },
    cases: [caseRecord],
    contracts: [contractRecord],
    caseFees: [caseFee],
  });
  assert.equal(result.ok, true);
  assert.deepEqual(result.payload.contract_record_id, 77);
  assert.deepEqual(result.payload.case_record_id, 41);
  assert.deepEqual(result.payload.case_fee_ids, [901]);
  assert.equal(result.payload.customer, "客户甲");
  assert.equal(result.payload.amount, 123.45);
});

test("F14-12 invoice payload rejects unknown case instead of text-only association", () => {
  const result = buildInvoiceApplicationPayload({
    values: { case_no: "MISSING", amount: 1 },
    cases: [caseRecord],
    contracts: [contractRecord],
    caseFees: [caseFee],
  });
  assert.equal(result.ok, false);
  assert.match(result.error, /案件/);
});

test("F14-12 invoice payload rejects unknown contract id", () => {
  const result = buildInvoiceApplicationPayload({
    values: { case_no: "CASE-41", contract_record_id: 999, amount: 1 },
    cases: [caseRecord],
    contracts: [contractRecord],
    caseFees: [caseFee],
  });
  assert.equal(result.ok, false);
  assert.match(result.error, /合同/);
});

test("F14-12 invoice payload rejects case-fee ids from another case", () => {
  const result = buildInvoiceApplicationPayload({
    values: { case_no: "CASE-41", case_fee_ids: [902], amount: 1 },
    cases: [caseRecord],
    contracts: [contractRecord],
    caseFees: [caseFee],
  });
  assert.equal(result.ok, false);
  assert.match(result.error, /费用/);
});

test("F14-12 invoice payload requires a positive amount", () => {
  const result = buildInvoiceApplicationPayload({
    values: { case_no: "CASE-41", amount: 0 },
    cases: [caseRecord],
    contracts: [contractRecord],
    caseFees: [caseFee],
  });
  assert.equal(result.ok, false);
  assert.match(result.error, /金额/);
});

test("F14-18 internal fee exports use the XLS endpoint and never CSV", () => {
  const exportBlock = source.match(/const exportConfiguredRows = async[\s\S]*?const exportRefunds/)[0];
  const internalBranch = exportBlock.match(/activeRouteConfig\.source === "fees"[\s\S]*?const rows/)[0];
  assert.match(internalBranch, /\/finance\/internal-fees\/export/);
  assert.match(internalBranch, /responseType:\s*["']blob["']/);
  assert.match(internalBranch, /\.xls/);
  assert.match(internalBranch, /internalFeeExportRequestParams/);
  assert.doesNotMatch(internalBranch, /text\/csv/);
});

test("F14-18 internal export helper keeps scope, filters and selected ids", () => {
  const params = internalFeeExportRequestParams({
    scope: "company",
    initialView: "finance-internal-archive",
    query: { routeField0: "CASE-41", routeField7: "全部" },
    ids: [4, 4, 9],
  });
  assert.equal(params.scope, "company");
  assert.equal(params.case_no, "CASE-41");
  assert.equal(params.payment_status, "");
  assert.equal(params.ids, "4,9");
});

test("F14-19 archive route title and pending-archive default are explicit", () => {
  assert.match(source, /finance-internal-archive["']\s*:\s*["']内部提成-待归档/);
  assert.match(source, /finance-internal-archive[\s\S]{0,1000}待归档/);
});

test("F14-20 invoice form and detail navigation preserve real return context", () => {
  assert.match(source, /name="contract_record_id"/);
  assert.match(source, /name="case_fee_ids"/);
  assert.match(source, /rememberCaseDetailTarget/);
  assert.match(source, /rememberContractDetailTarget/);
  assert.match(source, /rememberCustomerDetailTarget/);
});

test("F14 errors retain backend detail messages", () => {
  assert.match(source, /error\?\.response\?\.data\?\.detail/);
});
