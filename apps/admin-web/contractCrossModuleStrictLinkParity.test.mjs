import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import { filterContractLinkedRows } from "./src/contractWorkflowPolicy.mjs";

const contractCenterSource = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("invoice and payment rows require consistent contract id and number when both are present", () => {
  const rows = [
    { id: 1, data: { contract_record_id: 41, contract_no: "HT-041" } },
    { id: 2, data: { contract_record_id: 41, contract_no: "HT-0410" } },
    { id: 3, data: { contract_record_id: 42, contract_no: "HT-041" } },
    { id: 4, data: { contract_record_id: 41 } },
    { id: 5, data: { contract_no: "HT-041" } },
  ];

  assert.deepEqual(
    filterContractLinkedRows(rows, { id: 41, serial_no: "HT-041" }).map((row) => row.id),
    [1, 4, 5],
  );
});

test("contract detail keeps the strict linker on both invoice and payment datasets", () => {
  assert.match(contractCenterSource, /filterContractLinkedRows\(invoiceResult\.value\.data\.items/);
  assert.match(contractCenterSource, /normalizeContractPaymentApplications\(paymentResult\.value\.data/);
});
