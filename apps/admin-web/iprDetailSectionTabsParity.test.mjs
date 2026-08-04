import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");
const legacyTabs = fs.readFileSync(new URL("../../../旧系统归档源码/SH.CRM.WEB/Areas/IPR/Views/Case/PartialView/CaseState.cshtml", import.meta.url), "utf8");
const legacyJs = fs.readFileSync(new URL("../../../旧系统归档源码/SH.CRM.WEB/Scripts/IPR/Case/Case.Create.CaseInfo.js.orig", import.meta.url), "utf8");

assert.match(
  legacyTabs,
  /<li class="active" id="liCaseFileList">[\s\S]*?文档信息[\s\S]*?费用信息[\s\S]*?资助明细/,
  "Legacy IPR case detail exposed document/fee/assisted-fee tabs.",
);

assert.match(
  legacyJs,
  /btnCaseFileList[\s\S]*?caseInfo\.CaseFile\.List\(\)/,
  "Legacy document tab loaded the case file list.",
);

assert.match(
  legacyJs,
  /btnARCaseFeeList[\s\S]*?caseInfo\.ARCaseFee\.List\(\)/,
  "Legacy fee tab loaded the receivable fee list.",
);

assert.match(
  legacyJs,
  /btnCaseAssistedFeeList[\s\S]*?caseInfo\.CaseAssistedFee\.List\(\)/,
  "Legacy assisted-fee tab loaded the assisted fee list.",
);

assert.match(center, /Tabs,\r?\n/, "IprCenterPage should import Tabs from antd.");
assert.match(center, /const \[iprDetailTab, setIprDetailTab\] = useState<string>\("files"\);/, "IPR detail should keep a controlled tab key.");
assert.match(
  center,
  /<Tabs\s+activeKey=\{iprDetailTab\}\s+onChange=\{setIprDetailTab\}\s+items=\{\[/,
  "IPR detail should render the legacy document/fee sections as tabs.",
);
assert.match(
  center,
  /label: "文档信息",[\s\S]*?title="案件文书与附件"[\s\S]*?title="案件文档目录"/,
  "Document tab should contain the document cards.",
);
assert.match(
  center,
  /label: "资助明细",[\s\S]*?title="资助明细"/,
  "Assisted-fee tab should contain the assisted fee card.",
);
assert.match(center, /title="案件文书与附件"[\s\S]*?onClick=\{refreshIprFiles\}>刷新<\/Button>/, "Document refresh action should be preserved in the tabbed view.");
assert.match(center, /title="资助明细"[\s\S]*?onClick=\{refreshAssistedFees\}>刷新<\/Button>/, "Assisted-fee refresh action should be preserved in the tabbed view.");
assert.match(center, /pagination=\{filesPagination\}/, "Document table should keep its server pagination.");
assert.match(center, /pagination=\{assistedFeesPagination\}/, "Assisted-fee table should keep its server pagination.");

console.log("ipr detail section tabs parity: PASS");