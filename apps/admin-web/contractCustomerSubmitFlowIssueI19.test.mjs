import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const contractSource = fs.readFileSync(
  new URL("./src/ContractCenterPage.tsx", import.meta.url),
  "utf8",
);

const sliceBetween = (source, startMarker, endMarker, label) => {
  const start = source.indexOf(startMarker);
  assert.notEqual(start, -1, `${label} start marker should exist`);
  const end = source.indexOf(endMarker, start + startMarker.length);
  assert.notEqual(end, -1, `${label} end marker should exist`);
  return source.slice(start, end);
};

const submitWizardSource = sliceBetween(
  contractSource,
  "const submitWizard = async () => {",
  "  const refreshWizard = async () => {",
  "submitWizard",
);

const createSealApplicationSource = sliceBetween(
  contractSource,
  "  const createSealApplication = async (forcedSubmit?: boolean) => {",
  "  const downloadAttachment = async (item: Attachment) => {",
  "createSealApplication",
);

const startSelectedSealSource = sliceBetween(
  contractSource,
  "  const startSelectedSeal = async (contract: Contract) => {",
  "  const startCaseFromContract = (contract: Contract) => {",
  "startSelectedSeal",
);

test("I19 customer-created contracts retain the legacy four-step workflow", () => {
  assert.match(
    contractSource,
    /CONTRACT_CREATE_STEP_TITLES = \["合同基本信息", "提交审批", "合同审批", "合同用印"\]/,
    "the customer entry uses the same persisted four-step contract workflow as the legacy UI",
  );
});

test("I19 sync-seal intent can submit while contract approval is pending", () => {
  assert.match(
    contractSource,
    /已选择同步用印[\s\S]{0,220}立即提交同步用印；合同审批与用印审批将分别流转。/,
    "the customer submit flow must preserve the chosen sync intent and expose its independent submission",
  );
});

test("I19 submit success returns to contract detail, not approval or seal workbench", () => {
  assert.match(
    submitWizardSource,
    /onNavigate\?\.\(`contract-detail-\$\{contract\.id\}-\$\{encodeURIComponent\(contract\.serial_no\)\}`\)/,
    "successful submit without sync seal must navigate to the contract detail route",
  );
  assert.match(
    submitWizardSource,
    /localStorage\.removeItem\(WIZARD_STORAGE_KEY\);\s*setOpen\(false\);\s*onNavigate\?\.\(`contract-detail-/s,
    "the create wizard should close before entering the detail page",
  );
  assert.match(
    submitWizardSource,
    /const syncSealRequested = Boolean\(values\.sync_seal\);[\s\S]*if \(syncSealRequested\) \{[\s\S]*setWizardStep\(3\)[\s\S]*else \{[\s\S]*onNavigate\?\.\(`contract-detail-/,
    "only an explicit sync-seal choice enters the seal step; otherwise submit returns to contract detail",
  );
  assert.match(
    submitWizardSource,
    /if \(syncSealRequested\) \{[\s\S]*sealForm\.setFieldsValue\([\s\S]*submit: false,[\s\S]*setWizardStep\(3\)/,
    "the sync-seal choice initializes the form before the user explicitly submits its independent approval",
  );
});

test("I19 approval actions appear only for the current approver while status is pending approval", () => {
  assert.match(
    contractSource,
    /const approvalTarget = reviewing \|\| wizardDraft;[\s\S]*const approvalCapabilities = approvalTarget\?\.data\.approval_capabilities;[\s\S]*current_approver[\s\S]*currentApproval\?\.approver[\s\S]*contractCapabilities\(approvalTarget,[\s\S]*canApproveCurrent: approvalCapabilities\?\.can_approve_current[\s\S]*\.canApprove/s,
    "approval action gate must honor the server-provided current-node capability with an exact username fallback",
  );
  assert.match(
    contractSource,
    /wizardDraft\?\.status === "审批中" && currentApproval && \(canActOnCurrentApproval \? \(/,
    "create-wizard approval buttons must be nested under the current-approver gate",
  );
  assert.match(
    contractSource,
    /reviewing\?\.status === "审批中" && canActOnCurrentApproval \? \(/,
    "review modal footer actions must require both pending approval status and current approver rights",
  );
});

test("I19 independent seal setup supports pending approval and approved contracts", () => {
  assert.match(
    contractSource,
    /const CONTRACT_SEAL_READY_STATUSES = \["审批中", "审批通过", "已完成", "履行中", "已通过"\];/,
    "pending, approved, in-performance, and completed contracts remain eligible for independent seal setup",
  );
  assert.match(
    startSelectedSealSource,
    /CONTRACT_SEAL_READY_STATUSES\.includes\(contract\.status\)/,
    "the independent seal entry must use the approved-contract status gate",
  );
  assert.match(
    startSelectedSealSource,
    /setWizardStep\(3\);[\s\S]*purpose: /,
    "approved contracts can still open the seal configuration step from the dedicated seal action",
  );
  assert.match(
    createSealApplicationSource,
    /contract\.status !== "审批中"\) localStorage\.removeItem\(WIZARD_STORAGE_KEY\)/,
    "pending contracts keep the wizard context until the independent seal flow is complete",
  );
  assert.match(
    createSealApplicationSource,
    /const submitApplication = forcedSubmit \?\? Boolean\(submitFromForm\);/,
    "a selected sync flow must honor the user's explicit submit action",
  );
  assert.match(
    createSealApplicationSource,
    /if \(submitApplication\) \{[\s\S]*const route = buildContractDetailRoute\(contract\);[\s\S]*onNavigate\?\.\(route\);/,
    "independently submitted seal applications return through the persisted contract detail route",
  );
});
