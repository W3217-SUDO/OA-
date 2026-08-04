import fs from "node:fs";
import assert from "node:assert/strict";

const source = fs.readFileSync(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");

assert.match(source, /const \[incomingAllocationTarget, setIncomingAllocationTarget\]/);
assert.match(source, /r\.allocations\?\.length/);
assert.match(source, /分配记录/);
assert.match(source, /历史分配记录/);
assert.match(source, /incomingAllocationTarget\?\.allocations/);
assert.match(source, /row\.transaction_id \|\| row\.receivable_plan_id/);

const historyModalSource = source.slice(
  source.indexOf("历史分配记录"),
  source.indexOf("</Modal>", source.indexOf("历史分配记录")),
);

assert.match(
  historyModalSource,
  /dataIndex: "contract_no"[\s\S]*?openContractDetail/,
);
assert.match(
  historyModalSource,
  /dataIndex: "case_no"[\s\S]*?openCaseDetail/,
);
console.log("financeIncomingAllocationHistoryParity: 7 assertions passed");
