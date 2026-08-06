import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import {
  CONTRACT_LIST_PAGE_SIZES,
  CONTRACT_QUERY_FIELDS,
  buildContractListRequestParams,
  canAccessContractView,
  contractAttachmentActionPolicy,
  contractListViewConfig,
  contractMenuEntries,
  extractContractErrorMessage,
  normalizeContractQuery,
  validateContractApprovalSubmission,
} from "./src/contractWorkflowPolicy.mjs";

const pageSource = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("contract menus preserve mine, department, company, and audit routes", () => {
  const keys = contractMenuEntries().map((item) => item.key);
  assert.deepEqual(keys, [
    "contract-mine",
    "contract-dept",
    "contract-company",
    "contract-audit-pending",
    "contract-audit-refused",
    "contract-audit-approved",
  ]);
  assert.equal(contractListViewConfig("contract-dept").scope, "department");
  assert.equal(contractListViewConfig("contract-company").scope, "company");
});

test("contract list config keeps legacy audit and department/company page defaults", () => {
  assert.deepEqual(CONTRACT_LIST_PAGE_SIZES, [10, 15, 20, 50, 100, 200]);
  assert.equal(contractListViewConfig("contract-mine").defaultPageSize, 15);
  assert.equal(contractListViewConfig("contract-dept").defaultPageSize, 15);
  assert.equal(contractListViewConfig("contract-company").defaultPageSize, 15);
  assert.equal(contractListViewConfig("contract-audit-pending").defaultPageSize, 15);
});

test("contract query matrix includes legacy fields and trims only text input", () => {
  assert.deepEqual(CONTRACT_QUERY_FIELDS, [
    "title", "serial_no", "type", "customer", "case_no", "fee_type", "signed_at", "source_person", "contract_body",
  ]);
  assert.deepEqual(normalizeContractQuery({ title: "  合同  ", serial_no: "", signed_at: ["a", "b"] }), {
    title: "合同",
    serial_no: undefined,
    signed_at: ["a", "b"],
  });
});

test("contract list request keeps view scope, page, size, and query filters together", () => {
  const params = buildContractListRequestParams("contract-dept", { current: 2, pageSize: 50 }, {
    title: "合同",
    serial_no: "HT-1",
    signed_at: [{ format: () => "2026-01-01" }, { format: () => "2026-01-31" }],
  });
  assert.deepEqual(params, {
    module: "contract",
    scope: "department",
    page: 2,
    page_size: 50,
    title: "合同",
    serial_no: "HT-1",
    signed_at_start: "2026-01-01",
    signed_at_end: "2026-01-31",
  });
});

test("unknown contract routes fail closed while authenticated roles retain menus", () => {
  assert.equal(canAccessContractView("contract-mine", { role: "staff" }), true);
  assert.equal(canAccessContractView("contract-audit-pending", { role: "admin" }), true);
  assert.equal(canAccessContractView("contract-audit-pending", { role: "guest" }), false);
  assert.equal(canAccessContractView("contract-unknown", { role: "admin" }), false);
});

test("approval submission rejects wrong status, missing approver, and missing attachment", () => {
  assert.deepEqual(validateContractApprovalSubmission("已归档", "admin", 1), ["status"]);
  assert.deepEqual(validateContractApprovalSubmission("草稿", "", 1), ["approver"]);
  assert.deepEqual(validateContractApprovalSubmission("草稿", "admin", 0), ["attachment"]);
  assert.deepEqual(validateContractApprovalSubmission("草稿", "admin", 1), []);
});

test("approval and attachment action policies expose safe failure recovery", () => {
  assert.deepEqual(contractAttachmentActionPolicy("草稿"), { canUpload: true, canDelete: true, canDownload: true, canPreview: true });
  assert.deepEqual(contractAttachmentActionPolicy("审批中"), { canUpload: false, canDelete: false, canDownload: true, canPreview: true });
  assert.equal(extractContractErrorMessage({ response: { data: { detail: "权限不足" } } }, "操作失败"), "权限不足");
  assert.equal(extractContractErrorMessage({ message: "网络失败" }, "操作失败"), "网络失败");
  assert.equal(extractContractErrorMessage({}, "操作失败"), "操作失败");
});

test("contract center integrates the fourth-batch route, query, approval, attachment, and recovery policies", () => {
  assert.match(pageSource, /contractListViewConfig\(initialView\)/);
  assert.match(pageSource, /const effectiveQuery = relationQuery/);
  assert.match(pageSource, /buildContractListRequestParams\(initialView, listPagination, effectiveQuery\)/);
  assert.match(pageSource, /normalizeContractQuery\(values\)/);
  assert.match(pageSource, /queryForm\.resetFields\(\)/);
  assert.match(pageSource, /onClick=\{clearQuery\}/);
  assert.match(pageSource, /validateContractApprovalSubmission\(/);
  assert.match(pageSource, /contractAttachmentActionPolicy\(/);
  assert.match(pageSource, /extractContractErrorMessage\(/);
});
