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
const oldCreateUpdateInvoke = fs.readFileSync(
  path.join(
    oldRoot,
    "Scripts",
    "AWS",
    "OfficialDocument",
    "AWS.OfficialDocument.CreateUpdate.Invoke.js",
  ),
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

test("SealCenter source attachment selector consumes paged contract/case attachments", () => {
  const sourceLoader = sliceBetween(page, "const selectedSourceRecord = useMemo", "const clearQuery = () =>");
  const createModal = sliceBetween(page, "<Form form={createForm}", "</Form>");

  assert.ok(
    sourceHas(sourceLoader, /sourceAttachmentPage/),
    "source attachment selector must track the current source attachment page.",
  );
  assert.ok(
    sourceHas(sourceLoader, /sourceAttachmentPageSize/),
    "source attachment selector must track page_size for source attachment requests.",
  );
  assert.ok(
    sourceHas(sourceLoader, /sourceAttachmentTotal/),
    "source attachment selector must preserve response.total instead of assuming the first page is complete.",
  );
  assert.ok(
    sourceHas(sourceLoader, /api\.get\("\/attachments"[\s\S]*?page:[\s\S]*?page_size:/),
    "source attachment loader must request /attachments with explicit page and page_size.",
  );
  assert.ok(
    !sourceHas(sourceLoader, /page_size:\s*200/),
    "source attachment selector must not hard-cap legacy contract/case attachment choices at the first 200 rows.",
  );
  assert.ok(
    sourceHas(createModal, /(loadMoreSourceAttachments|sourceAttachmentTotal|sourceAttachmentPage)/),
    "create modal must expose a way to consume additional source attachment pages.",
  );
});

test("SealCenter hides relation and source attachment fields for administrative seals", () => {
  const legacyInitSealType = sliceBetween(
    oldCreateUpdateInvoke,
    "function initSealType()",
    "$(document).ready",
  );
  assert.ok(
    sourceHas(
      legacyInitSealType,
      /else\s*\{[\s\S]*?\$\("\.case"\)\.hide\(\);[\s\S]*?\$\("\.contract"\)\.hide\(\);[\s\S]*?\$\("\.customer"\)\.hide\(\);[\s\S]*?\}/,
    ),
    "legacy administrative seal branch hid case, contract, and customer selectors",
  );

  const sourceLoader = sliceBetween(page, "const selectedUseType", "const clearQuery = () =>");
  const createModal = sliceBetween(page, "<Form form={createForm}", "</Form>");

  assert.ok(
    sourceHas(sourceLoader, /const isContractSeal = selectedUseType === "合同用印";/),
    "create form must name the contract seal branch from use_type",
  );
  assert.ok(
    sourceHas(sourceLoader, /const isCaseSeal = selectedUseType === "案件用印";/),
    "create form must name the case seal branch from use_type",
  );
  assert.ok(
    sourceHas(sourceLoader, /const showSourceRelationFields = isContractSeal \|\| isCaseSeal;/),
    "only contract/case seals should expose relation/source fields",
  );
  assert.ok(
    sourceHas(sourceLoader, /setFieldsValue\(\{[\s\S]*?customer:\s*undefined,[\s\S]*?case_no:\s*undefined,[\s\S]*?contract_no:\s*undefined,[\s\S]*?source_attachment_ids:\s*\[\],[\s\S]*?\}\)/),
    "switching to administrative seal must clear stale relation and source selections",
  );
  assert.ok(
    sourceHas(createModal, /\{showSourceRelationFields && \([\s\S]*?label="客户\/单位"/),
    "administrative seal must not render the customer selector",
  );
  assert.ok(
    sourceHas(createModal, /\{isCaseSeal && \([\s\S]*?label="关联案号"/),
    "case selector must render only for case seals",
  );
  assert.ok(
    sourceHas(createModal, /\{isContractSeal && \([\s\S]*?label="关联合同号"/),
    "contract selector must render only for contract seals",
  );
  assert.ok(
    sourceHas(createModal, /\{showSourceRelationFields && \([\s\S]*?label="来源附件"/),
    "source attachment selector must render only for contract/case seals",
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

  assert.equal(canSealAction("approve", { status: "pending" }), false);
  assert.equal(canSealAction("approve", { status: "pending", capabilities: { approve: true } }), true);
  assert.equal(canSealAction("reject", { status: "pending", action_keys: ["reject"] }), true);
  assert.equal(canSealAction("approve", { status: "stamping" }), false);
  assert.equal(canSealAction("stamp", { status: "stamping", capabilities: { stamp: true } }), true);
  assert.equal(canSealAction("archive", { status: "used", action_keys: ["archive"] }), true);
  assert.equal(canBatchWithdrawSealRows([{ status: "待审批" }, { status: "待用印" }]), true);
  assert.equal(canBatchStampSealRows([{ status: "stamping", action_keys: ["stamp"] }]), true);
  assert.equal(canBatchDeleteSealFiles("草稿", [1]), true);
  assert.equal(canViewSealAssetAudit({ manage_assets: true }), true);
  assert.equal(canViewSealAssetAudit({ action_keys: ["manage_assets"] }), true);
  assert.equal(canViewSealAssetAudit("admin"), false);
});
