import assert from "node:assert/strict";

import { CASE_CONTRACT_CONTEXT_KEY, buildCaseContractContext, rememberCaseContractContext } from "./caseContractPrefill.ts";

const context = buildCaseContractContext({
  id: 18,
  serial_no: "HT-20260824-001",
  title: "合同案件",
  customer: "北方客户",
  data: { customer_id: 7, customer_no: "KH-20260824-007" },
}, () => 1724457600000);

assert.deepEqual(context, {
  id: 18,
  serial_no: "HT-20260824-001",
  title: "合同案件",
  customer: "北方客户",
  customer_id: 7,
  customer_no: "KH-20260824-007",
  at: 1724457600000,
});
assert.equal(buildCaseContractContext({ id: 0, serial_no: "HT-002", title: "", customer: "客户" }), null);

const entries = new Map();
rememberCaseContractContext({ setItem: (key, value) => entries.set(key, value) }, context);
assert.deepEqual(JSON.parse(entries.get(CASE_CONTRACT_CONTEXT_KEY) || "{}"), context);
