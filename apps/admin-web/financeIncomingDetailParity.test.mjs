import fs from "node:fs";
import assert from "node:assert/strict";

const source = fs.readFileSync(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");

assert.match(source, /const \[incomingDetailTarget, setIncomingDetailTarget\]/);
assert.match(source, /setIncomingDetailTarget\(r\)/);

const detailSection = source.slice(
  source.indexOf("回款详情"),
  source.indexOf("</Modal>", source.indexOf("回款详情")),
);

assert.match(detailSection, /incomingDetailTarget\?\.receipt_no/);
assert.match(detailSection, /incomingDetailTarget\?\.payer_name/);
assert.match(detailSection, /incomingDetailTarget\?\.amount/);
assert.match(detailSection, /incomingDetailTarget\?\.allocations/);
assert.match(detailSection, /openContractDetail/);
assert.match(detailSection, /openCaseDetail/);

console.log("financeIncomingDetailParity: 8 assertions passed");
