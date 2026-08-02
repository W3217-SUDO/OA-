import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("contract detail preserves the legacy attachment entry and return context", () => {
  assert.match(source, /api\.get\("\/attachments", \{ params: \{ record_id: contract\.id \} \}\)/);
  assert.match(source, /setViewingAttachments\(attachmentResult\.status === "fulfilled"/);
  assert.match(source, /api\.post\("\/attachments", attachment\)/);
  assert.match(source, /api\.get\(`\/attachments\/\$\{item\.id\}\/download`/);
  assert.match(source, /api\.get\(`\/attachments\/\$\{item\.id\}\/preview`/);
  assert.match(source, /api\.delete\(`\/attachments\/\$\{item\.id\}`\)/);
  assert.match(source, /sessionStorage\.setItem\(CONTRACT_DETAIL_RETURN_VIEW_STORAGE_KEY, initialView\)/);
  assert.match(source, /onNavigate\?\.\(`contract-detail-\$\{contract\.id\}/);
  assert.match(source, /onNavigate\?\.\(consumeContractDetailReturnView\(\)\)/);
  assert.match(source, /description="暂无合同附件"/);
});
