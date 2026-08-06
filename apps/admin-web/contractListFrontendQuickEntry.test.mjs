import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

const sliceBetween = (text, startMarker, endMarker, label) => {
  const start = text.indexOf(startMarker);
  assert.notEqual(start, -1, `${label} start marker should exist`);
  const end = text.indexOf(endMarker, start + startMarker.length);
  assert.notEqual(end, -1, `${label} end marker should exist`);
  return text.slice(start, end);
};

const columnsSource = sliceBetween(source, "  const columns = [", "  const auditColumns = [", "contract list columns");
const openViewingSource = sliceBetween(source, "  const openViewing = async", "  const saveContractObject = async", "openViewing");

test("contract list exposes legacy draft/refused submit as a row-level wizard shortcut", () => {
  assert.match(
    source,
    /const openSubmitWizardFromList = async \(contract: Contract\) => \{/,
    "the list shortcut should use a dedicated handler instead of duplicating submit logic",
  );
  assert.match(
    source,
    /await loadWizardContext\(contract\.id\);[\s\S]*setWizardStep\(1\);[\s\S]*setOpen\(true\);/,
    "the shortcut must reuse the existing wizard submit step and validation",
  );
  assert.match(
    columnsSource,
    /key: "operations"[\s\S]*canOpenSubmitWizard\(r\)[\s\S]*openSubmitWizardFromList\(r\)[\s\S]*提交审批/,
    "draft/refused contracts should show a row-level 提交审批 action",
  );
});

test("contract list opens the detail page directly on the attachment tab", () => {
  assert.match(
    source,
    /const CONTRACT_DETAIL_TAB_STORAGE_KEY = "sunhold:contract-detail-active-tab";/,
    "the detail target tab should be persisted across list-to-detail navigation",
  );
  assert.match(
    source,
    /const \[detailActiveTab, setDetailActiveTab\] = useState\("objects"\);/,
    "contract detail should own a controllable active tab",
  );
  assert.match(
    openViewingSource,
    /sessionStorage\.setItem\(CONTRACT_DETAIL_TAB_STORAGE_KEY, normalizeContractDetailTabKey\(options\.detailTab\)\);/,
    "list navigation must store the requested detail tab before routing",
  );
  assert.match(
    source,
    /const openContractAttachments = \(contract: Contract\) => \{[\s\S]*openViewing\(contract, \{ detailTab: "attachments" \}\);[\s\S]*\};/,
    "the attachment shortcut should route through openViewing with an attachments tab target",
  );
  assert.match(
    columnsSource,
    /openContractAttachments\(r\)[\s\S]*合同附件/,
    "each contract row should expose a 合同附件 direct entry",
  );
  assert.match(
    source,
    /<Tabs[\s\S]*activeKey=\{detailActiveTab\}[\s\S]*onChange=\{handleContractDetailTabChange\}/,
    "the contract detail Tabs should honor the requested attachment tab",
  );
});

test("contract list restores legacy approval, related case, and re-upload shortcuts", () => {
  assert.match(
    source,
    /const openContractApprovalInfo = \(contract: Contract\) => \{[\s\S]*openViewing\(contract, \{ detailTab: "approvals" \}\);[\s\S]*\};/,
    "contract rows should open approval information directly",
  );
  assert.match(
    source,
    /const openContractRelatedCaseFromList = \(contract: Contract\) => \{[\s\S]*const data = contract\.data as Record<string, unknown>;[\s\S]*openRelatedCase\(data\.case_no \|\| data\.case_serial_no \|\| data\.related_case_no\);[\s\S]*\};/,
    "contract rows should preserve the old related-case shortcut",
  );
  assert.match(
    columnsSource,
    /openContractApprovalInfo\(r\)[\s\S]*审批信息/,
    "each contract row should expose 审批信息",
  );
  assert.match(
    columnsSource,
    /openContractRelatedCaseFromList\(r\)[\s\S]*关联案件/,
    "each contract row should expose 关联案件",
  );
  assert.match(
    columnsSource,
    /canOpenSubmitWizard\(r\)[\s\S]*openSubmitWizardFromList\(r\)[\s\S]*重新上传/,
    "draft/refused rows should reopen the persisted submit wizard for re-upload",
  );
});

test("contract main list exposes a legacy GO quick jumper on pagination", () => {
  assert.match(
    source,
    /pagination=\{\{current:listPagination\.current,pageSize:listPagination\.pageSize,showSizeChanger:true,pageSizeOptions:\[10,15,20,50,100,200\],showQuickJumper:\s*\{\s*goButton:\s*<Button size="small">GO<\/Button>\s*\}/,
    "the main contract list should expose the same GO quick-jump pagination affordance as legacy paging",
  );
});
