import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const here = path.dirname(fileURLToPath(import.meta.url));
const mainSource = fs.readFileSync(path.resolve(here, "../api-server/app/main.py"), "utf8");
const modelsSource = fs.readFileSync(path.resolve(here, "../api-server/app/models.py"), "utf8");

/**
 * This is an executable audit ledger, not an assertion that the locked
 * backend is already complete. Items marked 需串行改 main.py stay visible
 * until the API owner adds the missing contract surface and Python tests.
 */
export const contractBackendMatrix = [
  { id: "draft-create", status: "已映射", local: "POST /contracts", evidence: "ContractDraftInput BusinessRecord WorkflowEvent" },
  { id: "draft-update", status: "已映射", local: "PATCH /contracts/{id}", evidence: "owner/manager guard and draft status" },
  { id: "submit", status: "已映射", local: "POST /contracts/{id}/submit", evidence: "ContractSubmitInput ContractApprovalStep WorkflowEvent" },
  { id: "approve-reject", status: "已映射", local: "POST /contracts/{id}/approve", evidence: "assigned approver/admin guard and status event" },
  { id: "approval-detail", status: "已映射", local: "GET /contracts/{id}/approvals", evidence: "steps/current_step response" },
  { id: "attachment-read", status: "已映射", local: "GET /attachments and download/preview", evidence: "FileAttachment visibility and path guard" },
  { id: "attachment-write", status: "已映射", local: "POST/DELETE /attachments", evidence: "owner/manager lock and size/type guard" },
  { id: "contract-events", status: "已映射", local: "GET/POST /contracts/{id}/events", evidence: "ContractEvent and WorkflowEvent" },
  { id: "object-case-finance", status: "已映射", local: "contract objects/cases/payment routes", evidence: "contract-linked records" },
  { id: "audit-list", status: "后端缺失", local: "dedicated pending/rejected/approved list", evidence: "generic records route has no current auditor matrix" },
  { id: "legacy-query-fields", status: "后端缺失", local: "title/serial/type/customer/case/fee/date/body filters", evidence: "records only accepts keyword and record_status" },
  { id: "scope-filter", status: "已映射", local: "mine/department/company scope", evidence: "records endpoint applies contract scope server-side" },
  { id: "server-page-sizes", status: "后端缺失", local: "10/15/20/50/100/200 defaults", evidence: "generic endpoint caps page_size at 100" },
  { id: "customer-contract-query", status: "后端缺失", local: "customer-linked contract query", evidence: "no dedicated old service equivalent" },
  { id: "draft-multi-upload", status: "后端缺失", local: "legacy draft multi-file response", evidence: "only generic single-file upload exists" },
  { id: "attachment-audit-events", status: "需串行改 main.py", local: "contract attachment upload/delete audit", evidence: "contract branch writes FileAttachment but no WorkflowEvent" },
  { id: "legacy-error-envelope", status: "需串行改 main.py", local: "PostResponse/error text parity", evidence: "local HTTP errors differ from legacy messages" },
];

test("contract backend matrix keeps three-way disposition explicit", () => {
  const statuses = new Set(contractBackendMatrix.map((item) => item.status));
  assert.deepEqual([...statuses].sort(), ["已映射", "后端缺失", "需串行改 main.py"].sort());
  assert.ok(contractBackendMatrix.filter((item) => item.status === "已映射").length >= 8);
  assert.ok(contractBackendMatrix.some((item) => item.status === "后端缺失"));
  assert.ok(contractBackendMatrix.some((item) => item.status === "需串行改 main.py"));
});

test("mapped backend contract symbols remain present in local API and models", () => {
  for (const pattern of [
    /@app\.post\(f?\"?\$?\{settings\.api_prefix\}\/contracts/,
    /@app\.get\(f?\"?\$?\{settings\.api_prefix\}\/attachments/,
    /ContractDraftInput/,
    /ContractSubmitInput/,
    /ContractApprovalInput/,
    /_require_contract_attachment_write_access/,
    /ContractApprovalStep/,
    /FileAttachment/,
    /WorkflowEvent/,
  ]) {
    assert.match(mainSource + modelsSource, pattern);
  }
});

test("matrix points to the known server-side debt instead of masking it", () => {
  const recordsSignature = mainSource.match(/async def list_records\([\s\S]*?\n\):/u)?.[0] || "";
  assert.match(recordsSignature, /keyword/);
  assert.match(recordsSignature, /record_status/);
  assert.match(recordsSignature, /scope/);
  assert.doesNotMatch(recordsSignature, /case_no/);
  assert.equal(contractBackendMatrix.find((item) => item.id === "scope-filter")?.status, "已映射");
  assert.equal(contractBackendMatrix.find((item) => item.id === "legacy-query-fields")?.status, "后端缺失");
});
