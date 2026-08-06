import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

const sliceBetween = (startMarker, endMarker, label) => {
  const start = source.indexOf(startMarker);
  assert.notEqual(start, -1, label + " start marker should exist");
  const end = source.indexOf(endMarker, start + startMarker.length);
  assert.notEqual(end, -1, label + " end marker should exist");
  return source.slice(start, end);
};

const revokeDraftSource = sliceBetween(
  "  const revokeDraft = (contract: Contract) => {",
  "  const archive = async (r: Contract) => {",
  "revokeDraft",
);

const approveWizardSource = sliceBetween(
  "  const approveWizard = async (approved: boolean) => {",
  "  const createSealApplication = async () => {",
  "approveWizard",
);

const approveSource = sliceBetween(
  "  const approve = async (approved: boolean) => {",
  "  const openChange = (r: Contract) => {",
  "approve",
);

const customerLinkSource = sliceBetween(
  "  const openRelatedCustomer = async (contract: Contract) => {",
  "  const openRelatedCase = async (caseNo: unknown) => {",
  "openRelatedCustomer",
);

test("draft revoke clears stale attachment, customer, wizard recovery, and seal state", () => {
  for (const pattern of [
    /localStorage\.removeItem\(WIZARD_STORAGE_KEY\);/,
    /setContractFile\(null\);/,
    /setSelectedAttachmentKeys\(\[\]\);/,
    /setAttachments\(\[\]\);/,
    /sealForm\.resetFields\(\);/,
    /setLinkedCustomerContext\(null\);/,
  ]) {
    assert.match(revokeDraftSource, pattern);
  }
  assert.match(
    revokeDraftSource,
    /message\.success\("合同草稿已撤销，附件和事项记录已一并清理"\);\s*void load\(\);/,
    "a successful revoke must close its confirmation before a list refresh can finish",
  );
  assert.doesNotMatch(
    revokeDraftSource,
    /message\.success\("合同草稿已撤销，附件和事项记录已一并清理"\);\s*await load\(\);/,
    "the confirmation must not wait on a potentially slow list refresh",
  );
});

test("wizard rejection returns to submit step and does not leave seal configuration behind", () => {
  assert.match(
    approveWizardSource,
    /const contract = await loadWizardContext\(wizardDraft\.id\);/,
    "wizard rejection should reload the contract, attachments, and approval history",
  );
  assert.match(
    approveWizardSource,
    /if \(!approved \|\| contract\.status === "已拒绝"\) \{[\s\S]*setWizardStep\(1\);[\s\S]*sealForm\.resetFields\(\);[\s\S]*setContractFile\(null\);[\s\S]*\}/,
    "a rejected contract must return to resubmission instead of retaining the approval/seal step",
  );
  assert.match(
    approveWizardSource,
    /if \(CONTRACT_SEAL_READY_STATUSES\.includes\(contract\.status\)\) \{/,
    "seal configuration must remain gated to approved-like statuses",
  );
});

test("review rejection refreshes open detail attachments and clears stale seal inputs", () => {
  assert.match(
    approveSource,
    /if \(!approved \|\| data\.contract\?\.status === "已拒绝"\) \{[\s\S]*sealForm\.resetFields\(\);[\s\S]*setContractFile\(null\);[\s\S]*setSelectedAttachmentKeys\(\[\]\);[\s\S]*\}/,
    "rejected review results must clear local seal and attachment selection state",
  );
  assert.match(
    approveSource,
    /if \(viewing\?\.id === data\.contract\?\.id\) \{[\s\S]*setViewing\(data\.contract\);[\s\S]*await reloadViewingAttachments\(data\.contract\);[\s\S]*await reloadDetailApprovals\(data\.contract\);[\s\S]*\}/,
    "an open contract detail should reload attachments and approval rows after rejection",
  );
});

test("customer linkage remains keyed to the refreshed contract after rejection", () => {
  assert.match(customerLinkSource, /Number\(contract\.data\.customer_id\)/);
  assert.match(customerLinkSource, /contract\.data\.customer_no/);
  assert.match(customerLinkSource, /contract\.customer/);
  assert.match(customerLinkSource, /rememberCustomerDetailTarget\(customer\);/);
  assert.match(customerLinkSource, /onNavigate\?\.\("customer-company"\);/);
});
