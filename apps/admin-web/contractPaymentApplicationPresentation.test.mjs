import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import { normalizeContractPaymentApplications } from "./src/contractPaymentApplicationPresentation.mjs";

const contractCenterSource = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("payment-applications preserves exact contract lines and exposes a readable line summary", () => {
  const rows = normalizeContractPaymentApplications({
    items: [{
      id: 7,
      serial_no: "CP-7",
      data: { contract_id: 41, contract_no: "HT-041", amount: 100 },
      lines: [
        { contract_object_id: 9, case_record_id: 91, case_no: "CN-091", fee_type: "官费", requested_amount: 60 },
        { contract_object_id: 10, case_record_id: 92, case_no: "CN-092", fee_type: "代理费", requested_amount: 40 },
      ],
    }],
    total: 1,
  }, { id: 41, serial_no: "HT-041" });

  assert.equal(rows.length, 1);
  assert.deepEqual(rows[0].lines, [
    { contract_object_id: 9, case_record_id: 91, case_no: "CN-091", fee_type: "官费", requested_amount: 60 },
    { contract_object_id: 10, case_record_id: 92, case_no: "CN-092", fee_type: "代理费", requested_amount: 40 },
  ]);
  assert.equal(rows[0].line_summary, "CN-091｜官费｜60.00；CN-092｜代理费｜40.00");
});

test("contract detail requests the dedicated payment-applications endpoint and renders its lines", () => {
  assert.match(contractCenterSource, /api\.get\(`\/contracts\/\$\{contract\.id\}\/payment-applications`\)/);
  assert.match(contractCenterSource, /normalizeContractPaymentApplications\(paymentResult\.value\.data/);
  assert.match(contractCenterSource, /line_summary/);
});
