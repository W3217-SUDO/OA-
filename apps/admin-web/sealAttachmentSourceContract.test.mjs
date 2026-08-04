import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { createRequire } from "node:module";
import ts from "typescript";

const page = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
const policyPath = path.join(process.cwd(), "src", "sealWorkflowPolicy.ts");
const policySource = fs.readFileSync(policyPath, "utf8");
const oldRoot = path.resolve(process.cwd(), "..", "..", "..", "旧系统归档源码", "SH.CRM.WEB");
const oldOfficialDocumentController = fs.readFileSync(
  path.join(oldRoot, "Areas", "AWS", "Controllers", "OfficialDocumentController.cs"),
  "utf8",
);

function sourceHas(source, pattern) {
  return pattern.test(source);
}

function sliceBetween(source, startToken, endToken) {
  const start = source.indexOf(startToken);
  assert.notEqual(start, -1, `missing source anchor: ${startToken}`);
  const end = source.indexOf(endToken, start + startToken.length);
  assert.notEqual(end, -1, `missing source end anchor: ${endToken}`);
  return source.slice(start, end);
}

function loadPolicy() {
  const javascript = ts.transpileModule(policySource, {
    fileName: policyPath,
    compilerOptions: {
      esModuleInterop: true,
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  const module = { exports: {} };
  const wrapper = vm.runInThisContext(
    `(function (require, module, exports, __filename, __dirname) { ${javascript}\n})`,
    { filename: policyPath },
  );
  wrapper(createRequire(import.meta.url), module, module.exports, policyPath, path.dirname(policyPath));
  return module.exports;
}

test("legacy official document creation copies contract and case source files", () => {
  assert.ok(
    sourceHas(oldOfficialDocumentController, /CreateByContract\(string id,string contractNo, string contractFileIds\)/),
    "legacy CreateByContract accepted selected contract file ids",
  );
  assert.ok(
    sourceHas(oldOfficialDocumentController, /ContractFileService\.Instance\.GetContractFile\(fileId\)/),
    "legacy CreateByContract loaded selected contract files",
  );
  assert.ok(
    sourceHas(oldOfficialDocumentController, /GetContractFileListByContractNo\(contractNo\)/),
    "legacy CreateByContract copied all contract files when ids were omitted",
  );
  assert.ok(
    sourceHas(oldOfficialDocumentController, /CreateByCase\(string id, string caseNo, string caseFileIds\)/),
    "legacy CreateByCase accepted selected case file ids",
  );
  assert.ok(
    sourceHas(oldOfficialDocumentController, /CaseFileService\.Instance\.GetCaseFile\(long\.Parse\(fileId\)\)/),
    "legacy CreateByCase loaded selected case files",
  );
  assert.ok(
    sourceHas(oldOfficialDocumentController, /OfficialDocumentFileService\.Instance\.CreateUpdate\(officialDocumentFile, bytes\)/),
    "legacy source files were persisted as official document files",
  );
});

test("SealCenter create modal exposes contract/case source attachment selectors", () => {
  const createModal = sliceBetween(page, "<Form form={createForm}", "</Form>");
  assert.ok(
    sourceHas(createModal, /(来源附件|合同附件|案件附件|源附件)/),
    "create seal application modal must show contract/case source attachment selection",
  );
  assert.ok(
    sourceHas(createModal, /(source_attachment_ids|contract_file_ids|case_file_ids)/),
    "source attachment selector must bind source_attachment_ids or explicit contract/case file id fields",
  );
  assert.ok(
    sourceHas(createModal, /mode=["']multiple["']|mode=\{["']multiple["']\}|checkbox|rowSelection/i),
    "source attachment selector must allow selecting multiple source files",
  );
});

test("SealCenter create request submits source attachment ids with the draft payload", () => {
  const createApplication = sliceBetween(page, "const createApplication = async", "const submit = async");
  assert.ok(
    sourceHas(createApplication, /(source_attachment_ids|contract_file_ids|case_file_ids)/),
    "createApplication must include selected source attachment ids in POST/PATCH payload",
  );
  assert.ok(
    sourceHas(createApplication, /postSeal\("\/seals\/applications",\s*data\)/),
    "new seal applications must still use the existing /seals/applications draft endpoint",
  );
  assert.ok(
    sourceHas(page, /api\.get\("\/attachments"[\s\S]*?(record_id|contract_no|case_no)/),
    "page must load selectable contract/case attachments instead of requiring re-upload",
  );
});

test("SealCenter preserves existing approval state and permission helper semantics", () => {
  const {
    canBatchDeleteSealFiles,
    canBatchStampSealRows,
    canBatchWithdrawSealRows,
    canSealAction,
    canViewSealAssetAudit,
  } = loadPolicy();

  assert.equal(canSealAction("approve", { status: "待审批" }), true);
  assert.equal(canSealAction("reject", { status: "待审批" }), true);
  assert.equal(canSealAction("approve", { status: "待用印" }), false);
  assert.equal(canSealAction("stamp", { status: "待用印" }), true);
  assert.equal(canSealAction("archive", { status: "已用印" }), true);
  assert.equal(canBatchWithdrawSealRows([{ status: "待审批" }, { status: "待用印" }]), true);
  assert.equal(canBatchStampSealRows([{ status: "待用印" }]), true);
  assert.equal(canBatchDeleteSealFiles("草稿", [1]), true);
  assert.equal(canViewSealAssetAudit("admin"), true);
  assert.equal(canViewSealAssetAudit("manager"), true);
  assert.equal(canViewSealAssetAudit("user"), false);
});
