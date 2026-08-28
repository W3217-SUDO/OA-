import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

import { buildContractCustomerQueryFromRelation } from "./src/contractCenterCustomerNavigation.ts";
import { buildCaseOrdinarySearchPayload } from "./src/caseOrdinarySearchParity.mjs";

const contractPage = await readFile(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");


test("customer contract navigation preserves stable identity and excludes archived contracts", () => {
  assert.deepEqual(buildContractCustomerQueryFromRelation({ id: 24, serial_no: "KH-R24", title: "测试客户1", target: "contracts" }), {
    customer_id: 24,
    customer_no: "KH-R24",
    customer: "测试客户1",
    exclude_archived: true,
  });
});

test("customer civil-case navigation sends identity and both civil type aliases", () => {
  const payload = buildCaseOrdinarySearchPayload(
    { customer_id: 24, customer_no: "KH-R24", customer: "测试客户1" },
    "mine",
    ["民事案件", "民事争议"],
    1,
    15,
  );
  assert.equal(payload.customer_id, 24);
  assert.equal(payload.customer_no, "KH-R24");
  assert.equal(payload.customer, "测试客户1");
  assert.deepEqual(payload.case_types, ["民事案件", "民事争议"]);
});

test("customer relation navigation replaces stale contract search fields", () => {
  assert.match(contractPage, /const effectiveQuery = relationQuery\s*\? \{ \.\.\.relationQuery \}\s*: baseQuery;/);
  assert.match(contractPage, /if \(relationQuery\) \{\s*queryForm\.resetFields\(\);\s*queryForm\.setFieldsValue\(relationQuery\);/);
  assert.doesNotMatch(contractPage, /\{ \.\.\.baseQuery,[^\n]+\.\.\.relationQuery \}/);
});
