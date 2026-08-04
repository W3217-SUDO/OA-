import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const legacy = fs.readFileSync(new URL("../../../旧系统归档源码/SH.CRM.WEB/Scripts/FCM/Contract/FCM.Contract.View.js", import.meta.url), "utf8");
const source = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("contract detail tabs reload the active legacy child view on switch", () => {
  assert.match(legacy, /#btnContractObjectList[\s\S]*?contract\.Contract\.Objects\.Layout\(\)/);
  assert.match(legacy, /#btnContractEventList[\s\S]*?contract\.Draft\.Events\.Layout\(\)/);
  assert.match(legacy, /#btnContractFileList[\s\S]*?contract\.Contract\.Files\.Layout\(\)/);
  assert.match(legacy, /#btnContractAuditList[\s\S]*?contract\.Contract\.Audits\.Layout\(\)/);

  assert.match(source, /const handleContractDetailTabChange = \(key: string\) => \{/);
  assert.match(source, /if \(!viewing \|\| key === detailActiveTab\) return;/);
  assert.match(source, /key === "attachments"[\s\S]*?reloadViewingAttachments\(viewing\)/);
  assert.match(source, /key === "events"[\s\S]*?reloadContractEvents\(viewing/);
  assert.match(source, /key === "approvals"[\s\S]*?reloadDetailApprovals\(viewing\)/);
  assert.match(source, /onChange=\{handleContractDetailTabChange\}/);
});
