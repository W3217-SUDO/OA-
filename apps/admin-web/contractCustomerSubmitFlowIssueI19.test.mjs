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
  "  const createSealApplication = async () => {",
  "  const downloadAttachment = async (item: Attachment) => {",
  "createSealApplication",
);

const startSelectedSealSource = sliceBetween(
  contractSource,
  "  const startSelectedSeal = async (contract: Contract) => {",
  "  const startCaseFromContract = (contract: Contract) => {",
  "startSelectedSeal",
);

test("I19 customer-created contracts do not split the submit stage into approval or seal steps", () => {
  const prematureWorkflowSteps = [
    ...contractSource.matchAll(/\["合同基本信息", "提交审批", "合同审批", "合同用印"\]\.map/g),
  ].map((match) => match.index);

  assert.deepEqual(
    prematureWorkflowSteps,
    [],
    "issue-list rows 16/17 require the customer-created contract submit stage to stop at 提交审批, not expose 合同审批/合同用印 before handoff",
  );
});

test("I19 customer submit flow does not offer sync-seal actions while contract approval is pending", () => {
  assert.doesNotMatch(
    contractSource,
    /合同已提交审批，可预先配置同步用印|保存同步用印资料|同步用印资料已保存，等待合同审批/,
    "a pending contract approval should not expose sync-seal setup from the customer submit flow",
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
    /if \(syncSealRequested\) \{[\s\S]*sealForm\.setFieldsValue\([\s\S]*submit: true,[\s\S]*setWizardStep\(3\)/,
    "the sync-seal choice must survive the approval context refresh and initialize the seal form",
  );
});

test("I19 approval actions appear only for the current approver while status is pending approval", () => {
  assert.match(
    contractSource,
    /const canActOnCurrentApproval = Boolean\(currentApproval && canActOnContractApproval\("审批中", currentApproval\.approver, profile\.username, profile\.role\)\);/,
    "approval action gate must include pending status, current approver, profile username, and role",
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
    /const CONTRACT_SEAL_READY_STATUSES = \["审批中", "已通过", "履行中", "已完成"\];/,
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
  assert.doesNotMatch(
    createSealApplicationSource,
    /同步用印资料/,
    "the seal save path must not preserve the removed pending-approval sync-seal wording",
  );
  assert.match(
    createSealApplicationSource,
    /onNavigate\?\.\("seal-my-pending"\)/,
    "a submitted sync-seal application must open the applicant pending list directly",
  );
});
